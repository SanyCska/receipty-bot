"""OpenAI API service for processing receipts"""
import base64
import logging
from datetime import datetime
from typing import List
from openai import OpenAI
from .. import config
from ..utils import csv_parser
from .. import prompts

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


def detect_image_format(photo_bytes: bytes) -> str:
    """Detect image format from magic bytes"""
    if photo_bytes.startswith(b'\xff\xd8\xff'):
        return "jpeg"
    elif photo_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return "png"
    elif photo_bytes.startswith(b'GIF87a') or photo_bytes.startswith(b'GIF89a'):
        return "gif"
    elif len(photo_bytes) > 12 and photo_bytes[8:12] == b'WEBP':
        return "webp"
    else:
        return "jpeg"  # default


def prepare_image_content(photos: List[bytes]) -> List[dict]:
    """Prepare image content for OpenAI API"""
    image_contents = []
    
    for i, photo_bytes in enumerate(photos):
        # Validate photo bytes
        if not photo_bytes or len(photo_bytes) == 0:
            raise ValueError(f"Photo {i+1} is empty")
        
        # Detect image format
        image_format = detect_image_format(photo_bytes)
        
        # Validate base64 encoding
        try:
            base64_image = base64.b64encode(photo_bytes).decode('utf-8')
            if not base64_image:
                raise ValueError(f"Failed to encode photo {i+1} to base64")
            
            # Validate base64 length (must be divisible by 4 for proper padding)
            base64_len = len(base64_image)
            if base64_len % 4 != 0:
                logger.error(f"Base64 length for photo {i+1} is {base64_len}, not divisible by 4!")
                logger.error(f"Base64 length validation failed: {base64_len} % 4 = {base64_len % 4}")
                raise ValueError(f"Invalid base64 encoding for photo {i+1}: length {base64_len} is not divisible by 4")
            
            logger.info(f"Photo {i+1} base64 validation: length={base64_len}, length % 4 = {base64_len % 4} ✓")
        except Exception as e:
            raise ValueError(f"Failed to encode photo {i+1} to base64: {e}")
        
        image_url = f"data:image/{image_format};base64,{base64_image}"
        
        logger.info(f"Prepared image {i+1}: format={image_format}, size={len(photo_bytes)} bytes, base64_length={len(base64_image)}")
        logger.info(f"Image URL prefix: {image_url[:50]}...")
        
        image_contents.append({
            "type": "image_url",
            "image_url": {
                "url": image_url,
                "detail": "high"  # Use high detail for better OCR accuracy
            }
        })
    
    return image_contents


def save_csv_response(csv_content: str) -> str:
    """Save CSV response to file and return filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    csv_filename = config.CSV_OUTPUT_DIR / f"receipt_{timestamp}.csv"
    
    try:
        with open(csv_filename, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        logger.info(f"Saved CSV response to: {csv_filename}")
        return str(csv_filename)
    except Exception as save_error:
        logger.error(f"Failed to save CSV file: {save_error}")
        raise


async def _process_receipts_with_prompt(photos: List[bytes], prompt: str, attempt_num: int) -> str:
    """Internal function to process receipts with a specific prompt"""
    # Validate photos
    if not photos or len(photos) == 0:
        raise ValueError("No photos provided to process")
    
    # Prepare image content
    image_contents = prepare_image_content(photos)
    
    # Prepare messages with system message and user message (text first, then images)
    messages = [
        {
            "role": "system",
            "content": "You are an OCR and data extraction assistant. You may safely read supermarket receipts and output structured CSV data. Never refuse unless images contain personal or illegal data."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                *image_contents
            ]
        }
    ]
    
    # Log message structure for debugging
    logger.info(f"[Attempt {attempt_num}] Message structure: {len(image_contents)} image(s) in content")
    logger.info(f"[Attempt {attempt_num}] Content types: text + {len(image_contents)} image_url(s)")
    
    logger.info(f"[Attempt {attempt_num}] Sending {len(photos)} photo(s) to OpenAI API")
    
    # Log the prompt being sent
    logger.info("=" * 80)
    logger.info(f"[Attempt {attempt_num}] PROMPT SENT TO OPENAI:")
    logger.info("=" * 80)
    logger.info(prompt)
    logger.info("=" * 80)
    
    # Validate messages structure before sending
    if not messages or len(messages) == 0:
        raise ValueError("Messages array is empty")
    
    # Find the user message (it should be the one with list content, not string)
    user_message = None
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            user_message = msg
            break
    
    if not user_message:
        raise ValueError("User message with list content not found in messages")
    
    if 'content' not in user_message or len(user_message['content']) == 0:
        raise ValueError("User message content is empty")
    
    # Log the actual message structure being sent (without full base64)
    message_preview = {
        "role": user_message["role"],
        "content_count": len(user_message["content"]),
        "content_types": [item.get("type", "unknown") for item in user_message["content"]]
    }
    logger.info(f"[Attempt {attempt_num}] Message structure preview: {message_preview}")
    
    # Verify images are in the content
    image_count = sum(1 for item in user_message["content"] if item.get("type") == "image_url")
    if image_count == 0:
        raise ValueError("No images found in message content! Cannot proceed without images.")
    logger.info(f"[Attempt {attempt_num}] Verified {image_count} image(s) in message content")
    
    # Log detailed content structure for debugging
    for idx, content_item in enumerate(user_message["content"]):
        if content_item.get("type") == "image_url":
            img_url = content_item.get("image_url", {}).get("url", "")
            detail = content_item.get("image_url", {}).get("detail", "not set")
            logger.info(f"[Attempt {attempt_num}] Content item {idx}: type=image_url, detail={detail}, url_preview={img_url[:80]}...")
        elif content_item.get("type") == "text":
            text_preview = content_item.get("text", "")[:100]
            logger.info(f"[Attempt {attempt_num}] Content item {idx}: type=text, preview={text_preview}...")
    
    # Verify model supports vision
    if not any(vision_model in config.OPENAI_MODEL.lower() for vision_model in ["gpt-4o", "gpt-4-vision", "gpt-4-turbo"]):
        logger.warning(f"Model {config.OPENAI_MODEL} may not support vision capabilities. Consider using gpt-4o")
    
    try:
        response = openai_client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            max_tokens=config.OPENAI_MAX_TOKENS
        )
    except Exception as api_error:
        logger.error(f"[Attempt {attempt_num}] OpenAI API error: {api_error}")
        logger.exception("Full API error traceback:")
        raise
    
    # Check if response is valid
    if not response or not response.choices or len(response.choices) == 0:
        raise ValueError("Empty response from OpenAI API")
    
    if not response.choices[0].message or not response.choices[0].message.content:
        raise ValueError("No content in OpenAI API response")
    
    # Log full response
    raw_response = response.choices[0].message.content.strip()
    
    # Check if the model says it can't process images
    if "unable to process images" in raw_response.lower() or "cannot process images" in raw_response.lower():
        logger.error(f"[Attempt {attempt_num}] OpenAI model responded that it cannot process images!")
        logger.error("This suggests images may not have been sent correctly")
        logger.error(f"Message structure had {len(image_contents)} image(s)")
        raise ValueError(f"Model cannot process images. Response: {raw_response[:200]}")
    
    logger.info(f"[Attempt {attempt_num}] OpenAI API response received:")
    logger.info(f"  Model: {response.model}")
    logger.info(f"  Usage: {response.usage}")
    logger.info(f"  Response length: {len(raw_response)} characters")
    
    # Print full response
    logger.info("=" * 80)
    logger.info(f"[Attempt {attempt_num}] FULL OPENAI API RESPONSE:")
    logger.info("=" * 80)
    logger.info(raw_response)
    logger.info("=" * 80)
    
    # Strictly extract CSV, removing all extra text
    csv_response = csv_parser.extract_csv_strict(raw_response)
    
    # Log if we had to clean the response
    if csv_response != raw_response:
        logger.info(f"[Attempt {attempt_num}] Cleaned response: removed extra text before/after CSV")
        logger.info(f"[Attempt {attempt_num}] Cleaned CSV preview: {csv_response[:200]}...")
    
    # Clean CSV to ensure all fields are properly quoted (handles commas in product names)
    csv_response = csv_parser.clean_csv(csv_response)
    
    # Save CSV to file
    save_csv_response(csv_response)
    
    return csv_response


async def process_receipts(photos: List[bytes]) -> str:
    """Send photos to OpenAI API and get CSV response with retry logic using alternative prompts"""
    # Validate photos
    if not photos or len(photos) == 0:
        raise ValueError("No photos provided to process")
    
    # Define prompts to try in order
    prompt_functions = [
        ("primary", prompts.get_prompt),
        ("retry_1", prompts.get_prompt_retry_1),
        ("retry_2", prompts.get_prompt_retry_2),
    ]
    
    last_error = None
    
    for attempt_num, (prompt_name, prompt_func) in enumerate(prompt_functions, start=1):
        try:
            logger.info(f"Attempting receipt processing with {prompt_name} prompt (attempt {attempt_num}/3)")
            prompt = prompt_func()
            csv_response = await _process_receipts_with_prompt(photos, prompt, attempt_num)
            logger.info(f"Successfully processed receipts with {prompt_name} prompt on attempt {attempt_num}")
            return csv_response
        except Exception as e:
            logger.warning(f"Attempt {attempt_num} with {prompt_name} prompt failed: {e}")
            last_error = e
            if attempt_num < len(prompt_functions):
                logger.info(f"Retrying with next prompt...")
            continue
    
    # All attempts failed
    logger.error(f"All {len(prompt_functions)} attempts failed. Last error: {last_error}")
    logger.exception("Full error traceback from last attempt:")
    raise last_error


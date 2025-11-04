"""OpenAI API service for processing receipts"""
import base64
import logging
from datetime import datetime
from typing import List
from openai import OpenAI
import config
import csv_parser
import prompts

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
        except Exception as e:
            raise ValueError(f"Failed to encode photo {i+1} to base64: {e}")
        
        image_url = f"data:image/{image_format};base64,{base64_image}"
        
        logger.info(f"Prepared image {i+1}: format={image_format}, size={len(photo_bytes)} bytes, base64_length={len(base64_image)}")
        logger.info(f"Image URL prefix: {image_url[:50]}...")
        
        image_contents.append({
            "type": "image_url",
            "image_url": {
                "url": image_url
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


async def process_receipts(photos: List[bytes]) -> str:
    """Send photos to OpenAI API and get CSV response"""
    prompt = prompts.get_prompt()
    
    # Validate photos
    if not photos or len(photos) == 0:
        raise ValueError("No photos provided to process")
    
    # Prepare image content
    image_contents = prepare_image_content(photos)
    
    # Prepare messages
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                *image_contents
            ]
        }
    ]
    
    # Log message structure for debugging
    logger.info(f"Message structure: {len(image_contents)} image(s) in content")
    logger.info(f"Content types: text + {len(image_contents)} image_url(s)")
    
    try:
        logger.info(f"Sending {len(photos)} photo(s) to OpenAI API")
        
        # Log the prompt being sent
        logger.info("=" * 80)
        logger.info("PROMPT SENT TO OPENAI:")
        logger.info("=" * 80)
        logger.info(prompt)
        logger.info("=" * 80)
        
        # Validate messages structure before sending
        if not messages or len(messages) == 0:
            raise ValueError("Messages array is empty")
        
        if 'content' not in messages[0] or len(messages[0]['content']) == 0:
            raise ValueError("Message content is empty")
        
        # Log the actual message structure being sent (without full base64)
        message_preview = {
            "role": messages[0]["role"],
            "content_count": len(messages[0]["content"]),
            "content_types": [item.get("type", "unknown") for item in messages[0]["content"]]
        }
        logger.info(f"Message structure preview: {message_preview}")
        
        try:
            response = openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                max_tokens=config.OPENAI_MAX_TOKENS
            )
        except Exception as api_error:
            logger.error(f"OpenAI API error: {api_error}")
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
            logger.error("OpenAI model responded that it cannot process images!")
            logger.error("This suggests images may not have been sent correctly")
            logger.error(f"Message structure had {len(image_contents)} image(s)")
            raise ValueError(f"Model cannot process images. Response: {raw_response[:200]}")
        
        logger.info(f"OpenAI API response received:")
        logger.info(f"  Model: {response.model}")
        logger.info(f"  Usage: {response.usage}")
        logger.info(f"  Response length: {len(raw_response)} characters")
        
        # Print full response
        logger.info("=" * 80)
        logger.info("FULL OPENAI API RESPONSE:")
        logger.info("=" * 80)
        logger.info(raw_response)
        logger.info("=" * 80)
        
        # Strictly extract CSV, removing all extra text
        csv_response = csv_parser.extract_csv_strict(raw_response)
        
        # Log if we had to clean the response
        if csv_response != raw_response:
            logger.info("Cleaned response: removed extra text before/after CSV")
            logger.info(f"Cleaned CSV preview: {csv_response[:200]}...")
        
        # Save CSV to file
        save_csv_response(csv_response)
        
        return csv_response
    except Exception as e:
        logger.error(f"Error processing receipts with OpenAI: {e}")
        logger.exception("Full error traceback:")
        raise


"""Main Telegram bot application"""
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import config
import csv_parser
import openai_service
import formatters
import telegram_utils

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Привет! Отправьте мне фотографии чеков из магазина, и я обработаю их.\n\n"
        "Просто отправьте одну или несколько фотографий чеков."
    )


async def process_media_group(media_group_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process all photos in a media group after waiting for all to arrive"""
    # Wait for all photos to arrive (Telegram sends them quickly but separately)
    max_wait_time = config.MEDIA_GROUP_MAX_WAIT_TIME
    check_interval = config.MEDIA_GROUP_CHECK_INTERVAL
    idle_threshold = config.MEDIA_GROUP_IDLE_THRESHOLD
    waited = 0.0
    
    while waited < max_wait_time:
        await asyncio.sleep(check_interval)
        waited += check_interval
        
        # Check if we have the media group and if it's still being updated
        if media_group_id in telegram_utils.media_groups:
            last_update = telegram_utils.media_groups[media_group_id]['last_update']
            time_since_update = (datetime.now() - last_update).total_seconds()
            
            # If no new photos arrived for threshold time, assume all photos are collected
            if time_since_update >= idle_threshold:
                break
    
    # Get all collected photos
    if media_group_id not in telegram_utils.media_groups:
        return
    
    photos_to_process = telegram_utils.media_groups[media_group_id]['photos'].copy()
    num_photos = len(photos_to_process)
    
    # Clean up immediately to avoid duplicate processing
    del telegram_utils.media_groups[media_group_id]
    
    if num_photos == 0:
        return
    
    # Send processing message
    if num_photos > 1:
        await update.message.reply_text(f"📸 Обрабатываю {num_photos} фото в одном запросе... Пожалуйста, подождите.")
    else:
        await update.message.reply_text("📸 Обрабатываю фото... Пожалуйста, подождите.")
    
    try:
        # Process all photos in one API request
        logger.info(f"Processing {num_photos} photos in single API request for media_group_id: {media_group_id}")
        csv_response = await openai_service.process_receipts(photos_to_process)
        products = csv_parser.parse_csv(csv_response)
        readable_message = formatters.format_readable_message(products)
        
        # Split message if too long
        message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH)
        for chunk in message_chunks:
            await update.message.reply_text(chunk)
            
    except Exception as e:
        logger.error(f"Error handling media group: {e}")
        logger.exception("Full error traceback:")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке чеков. Попробуйте еще раз или проверьте качество фото."
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    media_group_id = update.message.media_group_id
    
    # Download photo
    photo_bytes = await telegram_utils.download_photo(update, context)
    
    if media_group_id:
        # Add to media group collection
        current_time = datetime.now()
        
        if media_group_id not in telegram_utils.media_groups:
            # First photo in the group - start collection and schedule processing
            telegram_utils.media_groups[media_group_id] = {
                'photos': [photo_bytes],
                'last_update': current_time,
                'update_obj': update,
                'context': context
            }
            logger.info(f"Starting media group collection: {media_group_id}")
            
            # Notify user
            await update.message.reply_text(f"📸 Получено фото 1, ожидаю остальные...")
            
            # Schedule processing task (will wait for all photos)
            asyncio.create_task(process_media_group(media_group_id, update, context))
        else:
            # Additional photo in existing group
            telegram_utils.media_groups[media_group_id]['photos'].append(photo_bytes)
            telegram_utils.media_groups[media_group_id]['last_update'] = current_time
            num_collected = len(telegram_utils.media_groups[media_group_id]['photos'])
            logger.info(f"Added photo to media group {media_group_id}, total: {num_collected}")
            await update.message.reply_text(f"📸 Получено фото {num_collected}...")
    else:
        # Single photo - process immediately
        await update.message.reply_text("📸 Обрабатываю фото... Пожалуйста, подождите.")
        
        try:
            logger.info("Processing single photo")
            csv_response = await openai_service.process_receipts([photo_bytes])
            products = csv_parser.parse_csv(csv_response)
            readable_message = formatters.format_readable_message(products)
            
            # Split message if too long
            message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH)
            for chunk in message_chunks:
                await update.message.reply_text(chunk)
                
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            logger.exception("Full error traceback:")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке чека. Попробуйте еще раз или проверьте качество фото."
            )


def main():
    """Start the bot"""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        logger.error("Please create a .env file with TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables. Create a .env file.")
    
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment variables")
        logger.error("Please create a .env file with TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
        raise ValueError("OPENAI_API_KEY not found in environment variables. Create a .env file.")
    
    # Create application
    try:
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # Start bot
        logger.info("Bot started successfully")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    main()

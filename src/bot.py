"""Main Telegram bot application"""
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

from . import config
from .utils import csv_parser
from .services import openai_service
from .utils import formatters
from .utils import telegram_utils
from .services import gs_service
from .utils import currency_storage

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_CURRENCY = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Привет! Отправьте мне фотографии чеков из магазина, и я обработаю их.\n\n"
        "Просто отправьте одну или несколько фотографий чеков."
    )


async def ask_for_currency(update: Update, context: ContextTypes.DEFAULT_TYPE, csv_response: str, products: list):
    """Ask user to select currency for the receipt"""
    user_id = update.effective_user.id
    
    # Get user's currency preferences
    user_currencies = currency_storage.get_user_currencies(user_id)
    
    # Create keyboard buttons
    keyboard = []
    row = []
    
    # Show up to 6 currencies (last used first) - this includes defaults if not used yet
    # We'll arrange them in rows of 2
    currencies_to_show = user_currencies[:6]  # Show up to 6 currencies
    
    for currency in currencies_to_show:
        row.append(InlineKeyboardButton(currency, callback_data=f"currency_{currency}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Add "Other" button
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Other", callback_data="currency_other")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store receipt data in context for later use
    context.user_data['pending_receipt_csv'] = csv_response
    context.user_data['pending_receipt_products'] = products
    
    await update.message.reply_text(
        "💱 Пожалуйста, выберите валюту чека:",
        reply_markup=reply_markup
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
        
        # Ask for currency selection
        await ask_for_currency(update, context, csv_response, products)
            
    except Exception as e:
        logger.error(f"Error handling media group: {e}")
        logger.exception("Full error traceback:")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке чеков. Попробуйте еще раз или проверьте качество фото."
        )


async def save_receipt_with_currency(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    """Save receipt to Google Sheets with currency"""
    csv_response = context.user_data.get('pending_receipt_csv')
    products = context.user_data.get('pending_receipt_products')
    
    if not csv_response or not products:
        logger.error("No pending receipt data found")
        return
    
    # Add currency to products
    for product in products:
        product['currency'] = currency
    
    # Write to Google Sheets if configured
    if config.GOOGLE_SHEETS_SPREADSHEET_ID:
        try:
            gs_service.write_products_to_sheet(
                products,
                config.GOOGLE_SHEETS_SPREADSHEET_ID,
                config.GOOGLE_SHEETS_TAB_NAME
            )
            logger.info(f"Successfully wrote data to Google Sheets with currency {currency}")
        except Exception as gs_error:
            logger.error(f"Error writing to Google Sheets: {gs_error}")
            logger.exception("Google Sheets error traceback:")
            # Send error message based on update type
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "❌ Ошибка при сохранении в Google Sheets, но валюта сохранена."
                )
            elif update.message:
                await update.message.reply_text(
                    "❌ Ошибка при сохранении в Google Sheets, но валюта сохранена."
                )
    else:
        logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID not configured, skipping Google Sheets write")
    
    # Clean up
    context.user_data.pop('pending_receipt_csv', None)
    context.user_data.pop('pending_receipt_products', None)


async def handle_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency button callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "currency_other":
        # User selected "Other", ask for custom currency
        await query.edit_message_text(
            "💱 Пожалуйста, введите трехбуквенный код валюты (например, GBP, JPY, CNY):"
        )
        context.user_data['waiting_for_custom_currency'] = True
        return WAITING_FOR_CURRENCY
    else:
        # User selected a predefined currency
        currency = callback_data.replace("currency_", "").upper()
        
        # Save currency preference
        currency_storage.add_user_currency(user_id, currency)
        
        # Save receipt with currency
        await save_receipt_with_currency(update, context, currency)
        
        await query.edit_message_text(f"✅ Валюта {currency} сохранена. Чек записан в Google Sheets.")
        return ConversationHandler.END


async def handle_custom_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom currency input"""
    if not context.user_data.get('waiting_for_custom_currency'):
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    currency_text = update.message.text.strip().upper()
    
    # Validate currency code (3 letters)
    if len(currency_text) != 3 or not currency_text.isalpha():
        await update.message.reply_text(
            "❌ Неверный формат. Пожалуйста, введите трехбуквенный код валюты (например, GBP, JPY, CNY):"
        )
        return WAITING_FOR_CURRENCY
    
    # Save currency preference
    currency_storage.add_user_currency(user_id, currency_text)
    
    # Save receipt with currency
    await save_receipt_with_currency(update, context, currency_text)
    
    context.user_data.pop('waiting_for_custom_currency', None)
    await update.message.reply_text(f"✅ Валюта {currency_text} сохранена. Чек записан в Google Sheets.")
    return ConversationHandler.END


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
            
            # Ask for currency selection
            await ask_for_currency(update, context, csv_response, products)
                
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
        
        # Create conversation handler for currency selection
        currency_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_currency_callback, pattern="^currency_")],
            states={
                WAITING_FOR_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_currency)],
            },
            fallbacks=[],
        )
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(currency_conv_handler)
        
        # Start bot
        logger.info("Bot started successfully")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    main()


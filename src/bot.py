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
WAITING_FOR_QUANTITY = 2
WAITING_FOR_PRICE = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Привет! Отправьте мне фотографии чеков из магазина, и я обработаю их.\n\n"
        "Просто отправьте одну или несколько фотографий чеков."
    )


async def display_products_with_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, products: list, currency: str = None):
    """Display products list with action buttons"""
    readable_message = formatters.format_readable_message(products, currency=currency)
    
    # Split message if too long (but leave room for buttons message)
    message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH - 200)
    for chunk in message_chunks[:-1]:
        await update.message.reply_text(chunk)
    
    # Last chunk or full message if not split
    last_message = message_chunks[-1] if message_chunks else readable_message
    
    # Add action buttons
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="action_edit")],
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="action_confirm"),
            InlineKeyboardButton("❌ Отменить", callback_data="action_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(last_message, reply_markup=reply_markup)


async def display_products_with_actions_from_query(query, context: ContextTypes.DEFAULT_TYPE, products: list, currency: str = None):
    """Display products list with action buttons from a callback query"""
    readable_message = formatters.format_readable_message(products, currency=currency)
    
    # Split message if too long (but leave room for buttons message)
    message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH - 200)
    
    # Send all chunks except the last one as new messages
    for chunk in message_chunks[:-1]:
        await query.message.reply_text(chunk)
    
    # Last chunk or full message if not split
    last_message = message_chunks[-1] if message_chunks else readable_message
    
    # Add action buttons
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="action_edit")],
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="action_confirm"),
            InlineKeyboardButton("❌ Отменить", callback_data="action_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(last_message, reply_markup=reply_markup)


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
        
        # Initialize quantity for each product (default 1 if not present)
        for product in products:
            if 'quantity' not in product:
                product['quantity'] = '1'
        
        # Store products and CSV in context
        context.user_data['pending_receipt_csv'] = csv_response
        context.user_data['pending_receipt_products'] = products
        
        # Ask for currency first, before displaying products
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
    
    # Set today's date in YYYY-MM-DD format if receipt_date is missing or empty
    today_date = datetime.now().strftime("%Y-%m-%d")
    for product in products:
        receipt_date = product.get('receipt_date', '').strip()
        if not receipt_date:
            product['receipt_date'] = today_date
            logger.info(f"Set receipt_date to today's date ({today_date}) for product: {product.get('original_product_name', 'Unknown')}")
    
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
        
        # Store currency in context
        context.user_data['selected_currency'] = currency
        
        # Add currency to products
        products = context.user_data.get('pending_receipt_products', [])
        for product in products:
            product['currency'] = currency
        
        # Display products with currency symbol
        await display_products_with_actions_from_query(query, context, products, currency)
        
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
    
    # Store currency in context
    context.user_data['selected_currency'] = currency_text
    
    # Add currency to products
    products = context.user_data.get('pending_receipt_products', [])
    for product in products:
        product['currency'] = currency_text
    
    # Display products with currency symbol
    await display_products_with_actions(update, context, products, currency=currency_text)
    
    context.user_data.pop('waiting_for_custom_currency', None)
    return ConversationHandler.END


async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action button callbacks (Edit, Confirm, Cancel)"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "action_edit":
        # Show products as buttons
        products = context.user_data.get('pending_receipt_products', [])
        if not products:
            await query.edit_message_text("❌ Ошибка: список товаров не найден.")
            return
        
        keyboard = []
        for idx, product in enumerate(products):
            product_name = product.get('translated_product_name', product.get('original_product_name', f'Товар {idx+1}'))
            # Truncate long names
            if len(product_name) > 50:
                product_name = product_name[:47] + "..."
            keyboard.append([InlineKeyboardButton(
                f"{idx+1}. {product_name}",
                callback_data=f"edit_product_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="action_back_to_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выберите товар для редактирования:",
            reply_markup=reply_markup
        )
    
    elif callback_data == "action_confirm":
        # Save receipt with already selected currency
        currency = context.user_data.get('selected_currency')
        products = context.user_data.get('pending_receipt_products', [])
        csv_response = context.user_data.get('pending_receipt_csv', '')
        
        if not products or not csv_response:
            await query.edit_message_text("❌ Ошибка: данные не найдены.")
            return
        
        if not currency:
            await query.edit_message_text("❌ Ошибка: валюта не выбрана.")
            return
        
        # Save receipt with currency
        await save_receipt_with_currency(update, context, currency)
        
        currency_symbol = currency_storage.get_currency_symbol(currency)
        await query.edit_message_text(f"✅ Чек сохранен в Google Sheets ({currency_symbol}).")
    
    elif callback_data == "action_cancel":
        # Cancel and clean up
        context.user_data.pop('pending_receipt_csv', None)
        context.user_data.pop('pending_receipt_products', None)
        context.user_data.pop('selected_currency', None)
        context.user_data.pop('editing_product_idx', None)
        context.user_data.pop('waiting_for_quantity', None)
        context.user_data.pop('waiting_for_price', None)
        await query.edit_message_text("❌ Отменено. Можете отправить новый чек.")


async def handle_product_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product selection for editing"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "action_back_to_list" or callback_data == "action_back_to_products":
        # Show products list with action buttons again
        products = context.user_data.get('pending_receipt_products', [])
        if not products:
            await query.edit_message_text("❌ Ошибка: список товаров не найден.")
            return
        
        currency = context.user_data.get('selected_currency')
        readable_message = formatters.format_readable_message(products, currency=currency)
        message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH - 200)
        last_message = message_chunks[-1] if message_chunks else readable_message
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать", callback_data="action_edit")],
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="action_confirm"),
                InlineKeyboardButton("❌ Отменить", callback_data="action_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(last_message, reply_markup=reply_markup)
        return
    
    if not callback_data.startswith("edit_product_"):
        return
    
    # Extract product index
    product_idx = int(callback_data.replace("edit_product_", ""))
    products = context.user_data.get('pending_receipt_products', [])
    
    if product_idx < 0 or product_idx >= len(products):
        await query.edit_message_text("❌ Ошибка: неверный индекс товара.")
        return
    
    # Store which product is being edited
    context.user_data['editing_product_idx'] = product_idx
    
    # Show edit options
    keyboard = [
        [InlineKeyboardButton("🔢 Кол-во", callback_data="edit_quantity")],
        [InlineKeyboardButton("💰 Цена", callback_data="edit_price")],
        [InlineKeyboardButton("❌ Удалить", callback_data="edit_delete")],
        [InlineKeyboardButton("◀️ Назад к списку товаров", callback_data="action_back_to_products")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    product = products[product_idx]
    product_name = product.get('translated_product_name', product.get('original_product_name', 'Товар'))
    await query.edit_message_text(
        f"Что изменить?\n\nТовар: {product_name}",
        reply_markup=reply_markup
    )


async def handle_edit_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edit type selection (Quantity, Price, Delete)"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    products = context.user_data.get('pending_receipt_products', [])
    product_idx = context.user_data.get('editing_product_idx')
    
    if product_idx is None or product_idx < 0 or product_idx >= len(products):
        await query.edit_message_text("❌ Ошибка: товар не найден.")
        return
    
    if callback_data == "edit_quantity":
        context.user_data['waiting_for_quantity'] = True
        await query.edit_message_text("Введите новое количество:")
        return WAITING_FOR_QUANTITY
    
    elif callback_data == "edit_price":
        context.user_data['waiting_for_price'] = True
        await query.edit_message_text("Введите новую цену:")
        return WAITING_FOR_PRICE
    
    elif callback_data == "edit_delete":
        # Delete product
        products.pop(product_idx)
        context.user_data['pending_receipt_products'] = products
        context.user_data.pop('editing_product_idx', None)
        
        # Update CSV if needed
        if products:
            # Rebuild CSV from products
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=['original_product_name', 'translated_product_name', 
                                                         'category', 'subcategory', 'price', 'receipt_date', 'currency'])
            writer.writeheader()
            for p in products:
                writer.writerow({
                    'original_product_name': p.get('original_product_name', ''),
                    'translated_product_name': p.get('translated_product_name', ''),
                    'category': p.get('category', 'Unknown'),
                    'subcategory': p.get('subcategory', 'Unknown'),
                    'price': p.get('price', '0'),
                    'receipt_date': p.get('receipt_date', ''),
                    'currency': p.get('currency', '')
                })
            context.user_data['pending_receipt_csv'] = output.getvalue()
        else:
            # No products left
            context.user_data.pop('pending_receipt_csv', None)
            await query.edit_message_text("❌ Все товары удалены. Отправьте новый чек.")
            return
        
        # Show updated list
        await show_updated_products_list(query, context, products)


async def handle_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity input"""
    if not context.user_data.get('waiting_for_quantity'):
        return ConversationHandler.END
    
    try:
        quantity = float(update.message.text.strip().replace(',', '.'))
        if quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть больше нуля. Попробуйте еще раз:")
            return WAITING_FOR_QUANTITY
        
        products = context.user_data.get('pending_receipt_products', [])
        product_idx = context.user_data.get('editing_product_idx')
        
        if product_idx is None or product_idx < 0 or product_idx >= len(products):
            await update.message.reply_text("❌ Ошибка: товар не найден.")
            context.user_data.pop('waiting_for_quantity', None)
            context.user_data.pop('editing_product_idx', None)
            return ConversationHandler.END
        
        # Update quantity
        products[product_idx]['quantity'] = str(quantity)
        context.user_data['pending_receipt_products'] = products
        context.user_data.pop('waiting_for_quantity', None)
        context.user_data.pop('editing_product_idx', None)
        
        # Update CSV
        import csv
        from io import StringIO
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['original_product_name', 'translated_product_name', 
                                                     'category', 'subcategory', 'price', 'receipt_date', 'currency'])
        writer.writeheader()
        for p in products:
            writer.writerow({
                'original_product_name': p.get('original_product_name', ''),
                'translated_product_name': p.get('translated_product_name', ''),
                'category': p.get('category', 'Unknown'),
                'subcategory': p.get('subcategory', 'Unknown'),
                'price': p.get('price', '0'),
                'receipt_date': p.get('receipt_date', ''),
                'currency': p.get('currency', '')
            })
        context.user_data['pending_receipt_csv'] = output.getvalue()
        
        # Show updated list
        await show_updated_products_list_message(update.message, context, products)
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите число (например, 2 или 2.5):")
        return WAITING_FOR_QUANTITY


async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle price input"""
    if not context.user_data.get('waiting_for_price'):
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.strip().replace(',', '.'))
        if price < 0:
            await update.message.reply_text("❌ Цена не может быть отрицательной. Попробуйте еще раз:")
            return WAITING_FOR_PRICE
        
        products = context.user_data.get('pending_receipt_products', [])
        product_idx = context.user_data.get('editing_product_idx')
        
        if product_idx is None or product_idx < 0 or product_idx >= len(products):
            await update.message.reply_text("❌ Ошибка: товар не найден.")
            context.user_data.pop('waiting_for_price', None)
            context.user_data.pop('editing_product_idx', None)
            return ConversationHandler.END
        
        # Update price
        products[product_idx]['price'] = str(price)
        context.user_data['pending_receipt_products'] = products
        context.user_data.pop('waiting_for_price', None)
        context.user_data.pop('editing_product_idx', None)
        
        # Update CSV
        import csv
        from io import StringIO
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['original_product_name', 'translated_product_name', 
                                                     'category', 'subcategory', 'price', 'receipt_date', 'currency'])
        writer.writeheader()
        for p in products:
            writer.writerow({
                'original_product_name': p.get('original_product_name', ''),
                'translated_product_name': p.get('translated_product_name', ''),
                'category': p.get('category', 'Unknown'),
                'subcategory': p.get('subcategory', 'Unknown'),
                'price': p.get('price', '0'),
                'receipt_date': p.get('receipt_date', ''),
                'currency': p.get('currency', '')
            })
        context.user_data['pending_receipt_csv'] = output.getvalue()
        
        # Show updated list
        await show_updated_products_list_message(update.message, context, products)
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите число (например, 100.50):")
        return WAITING_FOR_PRICE


async def show_updated_products_list(query_or_message, context: ContextTypes.DEFAULT_TYPE, products: list):
    """Show updated products list with action buttons"""
    currency = context.user_data.get('selected_currency')
    readable_message = formatters.format_readable_message(products, currency=currency)
    message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH - 200)
    last_message = message_chunks[-1] if message_chunks else readable_message
    
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="action_edit")],
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="action_confirm"),
            InlineKeyboardButton("❌ Отменить", callback_data="action_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(query_or_message, 'edit_message_text'):
        # It's a CallbackQuery
        await query_or_message.edit_message_text(last_message, reply_markup=reply_markup)
    else:
        # It's a Message
        await query_or_message.reply_text(last_message, reply_markup=reply_markup)


async def show_updated_products_list_message(message, context: ContextTypes.DEFAULT_TYPE, products: list):
    """Show updated products list with action buttons (for message updates)"""
    currency = context.user_data.get('selected_currency')
    readable_message = formatters.format_readable_message(products, currency=currency)
    message_chunks = formatters.split_long_message(readable_message, config.MAX_MESSAGE_LENGTH - 200)
    last_message = message_chunks[-1] if message_chunks else readable_message
    
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="action_edit")],
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="action_confirm"),
            InlineKeyboardButton("❌ Отменить", callback_data="action_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(last_message, reply_markup=reply_markup)


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
            
            # Initialize quantity for each product (default 1 if not present)
            for product in products:
                if 'quantity' not in product:
                    product['quantity'] = '1'
            
            # Store products and CSV in context
            context.user_data['pending_receipt_csv'] = csv_response
            context.user_data['pending_receipt_products'] = products
            
            # Ask for currency first, before displaying products
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
        
        # Create conversation handler for editing products
        edit_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_edit_type_callback, pattern="^edit_(quantity|price|delete)$")
            ],
            states={
                WAITING_FOR_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity_input)],
                WAITING_FOR_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input)],
            },
            fallbacks=[],
        )
        
        # Add handlers (order matters - more specific patterns first)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(CallbackQueryHandler(handle_product_selection, pattern="^edit_product_|^action_back_to_list$|^action_back_to_products$"))
        application.add_handler(CallbackQueryHandler(handle_action_callback, pattern="^action_"))
        application.add_handler(edit_conv_handler)
        application.add_handler(currency_conv_handler)
        
        # Start bot
        logger.info("Bot started successfully")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    main()


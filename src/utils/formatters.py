"""Message formatting utilities"""
from decimal import Decimal
from typing import List, Dict, Optional
import logging
from . import currency_storage

logger = logging.getLogger(__name__)


def format_readable_message(products: List[Dict[str, str]], currency: Optional[str] = None) -> str:
    """
    Format products into readable message
    
    Args:
        products: List of product dictionaries
        currency: Currency code (e.g., 'USD', 'EUR'). If None, uses 'RUB' as default
    """
    if not products:
        return "❌ Не удалось обработать чек. Попробуйте еще раз."
    
    # Get currency symbol
    if currency:
        currency_symbol = currency_storage.get_currency_symbol(currency)
    else:
        # Try to get currency from first product, or default to RUB
        currency = products[0].get('currency', 'RUB')
        currency_symbol = currency_storage.get_currency_symbol(currency)
    
    message = "📋 Обработанные товары:\n\n"
    
    # Group by category
    categories = {}
    total = Decimal('0')
    
    for product in products:
        category = product.get('category', 'Unknown')
        subcategory = product.get('subcategory', 'Unknown')
        price_str = product.get('price', '0').replace(',', '.')
        
        try:
            price = Decimal(price_str)
        except:
            price = Decimal('0')
        
        quantity_str = product.get('quantity', '1')
        try:
            quantity = Decimal(quantity_str)
        except:
            quantity = Decimal('1')
        
        # Calculate item total (price * quantity) and add to total
        item_total = price * quantity
        total += item_total
        
        category_key = f"{category} - {subcategory}"
        if category_key not in categories:
            categories[category_key] = []
        
        categories[category_key].append({
            'original': product.get('original_product_name', 'N/A'),
            'translated': product.get('translated_product_name', 'N/A'),
            'price': price,
            'quantity': quantity,
            'item_total': item_total
        })
    
    # Format by category
    for category_key, items in categories.items():
        message += f"🏷️ {category_key}\n"
        for item in items:
            message += f"  • {item['translated']} ({item['original']})\n"
            if item['quantity'] != Decimal('1'):
                message += f"    🔢 Кол-во: {item['quantity']}\n"
                message += f"    💰 Цена за единицу: {item['price']:.2f} {currency_symbol}\n"
                message += f"    💰 Всего: {item['item_total']:.2f} {currency_symbol}\n"
            else:
                message += f"    💰 {item['price']:.2f} {currency_symbol}\n"
        message += "\n"
    
    message += f"\n💰 Итого: {total:.2f} {currency_symbol}"
    
    return message


def split_long_message(message: str, max_length: int = 4000) -> List[str]:
    """Split long message into chunks"""
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    for i in range(0, len(message), max_length):
        chunks.append(message[i:i+max_length])
    
    return chunks


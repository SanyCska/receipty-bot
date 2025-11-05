"""Message formatting utilities"""
from decimal import Decimal
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def format_readable_message(products: List[Dict[str, str]]) -> str:
    """Format products into readable message"""
    if not products:
        return "❌ Не удалось обработать чек. Попробуйте еще раз."
    
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
            total += price
        except:
            price = Decimal('0')
        
        category_key = f"{category} - {subcategory}"
        if category_key not in categories:
            categories[category_key] = []
        
        categories[category_key].append({
            'original': product.get('original_product_name', 'N/A'),
            'translated': product.get('translated_product_name', 'N/A'),
            'price': price
        })
    
    # Format by category
    for category_key, items in categories.items():
        message += f"🏷️ {category_key}\n"
        for item in items:
            message += f"  • {item['translated']} ({item['original']})\n"
            message += f"    💰 {item['price']:.2f} ₽\n"
        message += "\n"
    
    message += f"\n💰 Итого: {total:.2f} ₽"
    
    return message


def split_long_message(message: str, max_length: int = 4000) -> List[str]:
    """Split long message into chunks"""
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    for i in range(0, len(message), max_length):
        chunks.append(message[i:i+max_length])
    
    return chunks


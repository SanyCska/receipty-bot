"""Prompt templates and category loading"""
import logging
from pathlib import Path
import config

logger = logging.getLogger(__name__)


def load_categories() -> str:
    """Load categories from CSV file and return as string for prompt"""
    try:
        with open(config.RECEIPT_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        return ""


def get_prompt() -> str:
    """Get the prompt for OpenAI API"""
    categories_csv = load_categories()
    
    prompt = """You will receive one or several photos of supermarket receipts.
        Please:
        
        Extract all product line items from each receipt, including:
        
        product name
        
        quantity (if available)
        
        price (total for that product)
        
        Validate that the sum of product prices matches the total receipt amount (just check internally, do not include explanation in output).
        
        Categorize each product using the provided receipt_categories.csv.
        
        Translate each product name into Russian.
        
        Return your final result strictly in CSV format, with the following columns:
        
        original_product_name,translated_product_name,category,subcategory,price
        
        
        ⚠️ Important:
        
        Output only raw CSV text — no explanations, no Markdown, no tables, no headers like "Here's the CSV".
        The first line must always be the exact header: original_product_name,translated_product_name,category,subcategory,price
        Do not wrap the CSV inside csv or ``` blocks.
        Do not include any extra text before or after the CSV.
        
        Every product from all receipts must appear in this CSV.
        
        Example of correct output (structure only):
        
        original_product_name,translated_product_name,category,subcategory,price
        Baguet sa belim lukom La Lorraine 165g,Багет с чесноком La Lorraine 165г,Food & Groceries,Bread,134.99
        Kisela pavlaka Moja Kravica 20%mm 180g,Сметана Moja Kravica 20% 180г,Food & Groceries,Milk & Cream,79.99

        
    """
    prompt += categories_csv
    
    return prompt


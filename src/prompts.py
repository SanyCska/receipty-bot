"""Prompt templates and category loading"""
import logging
from pathlib import Path
from . import config

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

    prompt = """You are analyzing one or more supermarket receipts (non-personal, sample data only).

    TASK:
    1. Read the attached receipt images using your vision capabilities.
    2. Extract the following information:
       - Every product line item, including:
           • product name
           • quantity (if available)
           • total price for that product
       - The purchase date shown on the receipt (e.g., "2025-11-04").
    3. Validate internally that the total sum of all products matches the receipt total (do not include this validation in output).
    4. Categorize each product into a main category and subcategory using the provided 'receipt_categories.csv' reference.
    5. Translate each product name into Russian.

    OUTPUT FORMAT (MANDATORY):
    Return ONLY a CSV table.  
    The CSV must ALWAYS start with this exact header:
    original_product_name,translated_product_name,category,subcategory,price,receipt_date

    Rules:
    - Include one line per product.
    - Enclose ALL text fields in double quotes ("...") to avoid comma conflicts.
    - Repeat the same receipt_date for all products from the same receipt.
    - The date format must be ISO-8601: YYYY-MM-DD (e.g., 2025-11-04).
    - Use English for category and subcategory.
    - Use '.' as the decimal separator for price.
    - Do NOT include explanations, markdown, code blocks, or any extra text.
    - Do NOT wrap the CSV in ```csv``` or ``` blocks.
    - If the receipt date is unreadable, leave the field blank but keep the column.

    Example:
    original_product_name,translated_product_name,category,subcategory,price,receipt_date
    "VODA GAZIRANA KNJAZ MILOS 0,33L","Газированная вода Knjaz Miloš 0,33L","Beverages","Soft Drinks & Juices",93.98,2025-10-31
    "Baguet sa belim lukom La Lorraine 165g","Багет с чесноком La Lorraine 165г","Food & Groceries","Bread",134.99,2025-11-04

    Categories reference (for classification assistance):
    """

    prompt += categories_csv
    
    return prompt


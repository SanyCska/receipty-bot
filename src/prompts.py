"""Prompt templates and category loading"""
import logging
import csv
from pathlib import Path
from typing import Dict, List
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


def load_categories_dict() -> Dict[str, List[str]]:
    """
    Load categories from CSV file and return as dictionary
    Returns: Dict with category_group as key and list of subcategories as value
    """
    categories_dict = {}
    try:
        with open(config.RECEIPT_CATEGORIES_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                category = row.get('category_group', '').strip()
                subcategory = row.get('subcategory', '').strip()
                if category and subcategory:
                    if category not in categories_dict:
                        categories_dict[category] = []
                    if subcategory not in categories_dict[category]:
                        categories_dict[category].append(subcategory)
        return categories_dict
    except Exception as e:
        logger.error(f"Error loading categories dictionary: {e}")
        return {}


def get_category_list() -> List[str]:
    """Get list of all unique categories"""
    categories_dict = load_categories_dict()
    return sorted(categories_dict.keys())


def get_subcategories_for_category(category: str) -> List[str]:
    """Get list of subcategories for a given category"""
    categories_dict = load_categories_dict()
    return sorted(categories_dict.get(category, []))


def get_prompt(language: str = "serbian") -> str:
    """Get the prompt for OpenAI API"""
    categories_csv = load_categories()

    prompt = f"""You are analyzing one or more supermarket receipts (non-personal, sample data only).
    
    Receipts will be on {language.lower()} language.

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


def get_prompt_retry_1(language: str = "serbian") -> str:
    """Get the first retry prompt for OpenAI API"""
    categories_csv = load_categories()
    
    prompt = f"""You are analyzing a supermarket receipts image.

Receipts will be on {language.lower()} language 

STRICT TASK:

1. Detect ALL product rows on the receipt.

2. For EACH product extract ONLY:

   - exact product name as written

   - total price for that product

3. Extract the receipt purchase date if visible.

4. Categorize EACH product using ONLY the provided categories.

5. Translate EACH product name into Russian.

CRITICAL RULES:

- Even if some data is unclear, you MUST still output one row per detected product.

- NEVER skip category assignment.

- NEVER skip translation.

- NEVER add commentary.

OUTPUT FORMAT (MANDATORY, STRICT):

original_product_name,translated_product_name,category,subcategory,price,receipt_date

Rules:

- One line per product.

- ALL text fields in double quotes.

- Decimal separator is '.'.

- Date must be YYYY-MM-DD or empty.

- NO markdown.

- NO explanations.

- NO validation text.

- NO JSON.

Categories reference (for classification assistance):
"""
    prompt += categories_csv
    
    return prompt


def get_prompt_retry_2(language: str = "serbian") -> str:
    """Get the second retry prompt for OpenAI API"""
    categories_csv = load_categories()
    
    prompt = f"""You are analyzing a receipt image.
    Receipts will be on {language.lower()} language.

TASK:

1. Extract ALL product rows.

2. For EACH product extract:

   - original product name

   - total product price

3. Extract receipt date if present.

4. Translate product names into Russian.

5. Categorize products using provided categories.

IMPORTANT:

- DO NOT validate or compare totals.

- DO NOT try to match receipt sum.

- DO NOT remove products if totals mismatch.

OUTPUT FORMAT (MANDATORY):

original_product_name,translated_product_name,category,subcategory,price,receipt_date

Rules:

- One product per row.

- All text fields in double quotes.

- Decimal separator is '.'.

- Date format YYYY-MM-DD or empty.

- NO explanations.

- NO markdown.

Categories reference:
"""
    prompt += categories_csv
    
    return prompt


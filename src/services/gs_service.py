"""Google Sheets service for writing receipt data"""
import logging
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict
from .. import config
from ..utils import csv_parser

logger = logging.getLogger(__name__)

# Google Sheets API scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_gs_client():
    """Initialize and return Google Sheets client"""
    try:
        creds = Credentials.from_service_account_file(
            str(config.GS_CREDS_PATH),
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        raise


def write_products_to_sheet(products: List[Dict[str, str]], spreadsheet_id: str, tab_name: str):
    """
    Write products to Google Sheet
    
    Args:
        products: List of product dictionaries with keys: original_product_name, 
                 translated_product_name, category, subcategory, price, receipt_date
        spreadsheet_id: Google Sheets spreadsheet ID
        tab_name: Name of the tab/sheet to write to
    """
    try:
        client = get_gs_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get or create the tab
        try:
            worksheet = spreadsheet.worksheet(tab_name)
            logger.info(f"Found existing tab: {tab_name}")
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Tab '{tab_name}' not found, creating new tab")
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=10)
        
        # Check if headers exist
        existing_headers = worksheet.row_values(1)
        existing_headers_lower = [h.lower() for h in existing_headers] if existing_headers else []
        
        # Define all headers including currency
        all_headers = ['original_product_name', 'translated_product_name', 'category', 'subcategory', 'price', 'receipt_date', 'currency']
        
        if not existing_headers or len(existing_headers) < 5:
            # Add headers if they don't exist
            worksheet.append_row(all_headers)
            logger.info("Added headers to sheet")
        else:
            # Check if currency header is missing
            if 'currency' not in existing_headers_lower:
                # Update headers to include currency
                worksheet.update('A1:G1', [all_headers])
                logger.info("Updated headers to include currency")
            elif 'receipt_date' not in existing_headers_lower:
                # Update headers to include receipt_date (but currency is already there)
                headers_without_currency = ['original_product_name', 'translated_product_name', 'category', 'subcategory', 'price', 'receipt_date', 'currency']
                worksheet.update('A1:G1', [headers_without_currency])
                logger.info("Updated headers to include receipt_date")
        
        # Get the next empty row
        next_row = len(worksheet.get_all_values()) + 1
        
        # Prepare data rows - duplicate products based on quantity
        rows_to_add = []
        for product in products:
            # Get quantity, default to 1 if not present or invalid
            quantity_str = product.get('quantity', '1')
            try:
                quantity = int(float(quantity_str))  # Handle both int and float strings
                if quantity < 1:
                    quantity = 1
            except (ValueError, TypeError):
                quantity = 1
            
            # Create row data
            row = [
                product.get('original_product_name', ''),
                product.get('translated_product_name', ''),
                product.get('category', ''),
                product.get('subcategory', ''),
                product.get('price', ''),
                product.get('receipt_date', ''),
                product.get('currency', '')
            ]
            
            # Duplicate the product based on quantity
            for _ in range(quantity):
                rows_to_add.append(row)
        
        # Append all rows at once (more efficient)
        if rows_to_add:
            worksheet.append_rows(rows_to_add)
            logger.info(f"Successfully wrote {len(rows_to_add)} rows to Google Sheet '{tab_name}' (from {len(products)} products with quantities)")
            return True
        else:
            logger.warning("No products to write to Google Sheet")
            return False
            
    except Exception as e:
        logger.error(f"Error writing to Google Sheet: {e}")
        logger.exception("Full error traceback:")
        raise


def write_csv_to_sheet(csv_content: str, spreadsheet_id: str, tab_name: str):
    """
    Write CSV content directly to Google Sheet
    
    Args:
        csv_content: CSV content as string
        spreadsheet_id: Google Sheets spreadsheet ID
        tab_name: Name of the tab/sheet to write to
    """
    try:
        products = csv_parser.parse_csv(csv_content)
        return write_products_to_sheet(products, spreadsheet_id, tab_name)
    except Exception as e:
        logger.error(f"Error writing CSV to Google Sheet: {e}")
        logger.exception("Full error traceback:")
        raise


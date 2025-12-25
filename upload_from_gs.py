#!/usr/bin/env python3
"""
Script to upload receipt data from Google Sheets to PostgreSQL database

This script reads data from a Google Sheet and imports it into the database,
associating it with a specific Telegram user.

Usage:
    python upload_from_gs.py --telegram-id <telegram_id> [--spreadsheet-id <id>] [--tab-name <name>]
    
Example:
    python upload_from_gs.py --telegram-id 123456789
    python upload_from_gs.py --telegram-id 123456789 --spreadsheet-id "abc123xyz" --tab-name "january_2025"
"""
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import db_service, gs_service
from src import config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def read_products_from_sheet(spreadsheet_id: str, tab_name: str) -> List[Dict[str, str]]:
    """
    Read products from Google Sheet
    
    Args:
        spreadsheet_id: Google Sheets spreadsheet ID
        tab_name: Name of the tab/sheet to read from
        
    Returns:
        List of product dictionaries
    """
    try:
        client = gs_service.get_gs_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get the worksheet
        worksheet = spreadsheet.worksheet(tab_name)
        logger.info(f"Reading data from tab: {tab_name}")
        
        # Get all values from the sheet
        all_values = worksheet.get_all_values()
        
        if not all_values:
            logger.warning("Sheet is empty")
            return []
        
        # First row should be headers
        headers = all_values[0]
        logger.info(f"Found headers: {headers}")
        
        # Normalize header names (lowercase, strip whitespace)
        headers_normalized = [h.lower().strip() for h in headers]
        
        # Map common variations to standard field names
        field_mapping = {
            'original_product_name': ['original_product_name', 'original product name', 'original name', 'product name'],
            'translated_product_name': ['translated_product_name', 'translated product name', 'translated name', 'translated'],
            'category': ['category'],
            'subcategory': ['subcategory', 'sub category', 'sub-category'],
            'price': ['price', 'amount'],
            'receipt_date': ['receipt_date', 'receipt date', 'date'],
            'currency': ['currency'],
            'quantity': ['quantity', 'qty']
        }
        
        # Create header index mapping
        header_indices = {}
        for standard_field, variations in field_mapping.items():
            for i, header in enumerate(headers_normalized):
                if header in variations:
                    header_indices[standard_field] = i
                    break
        
        logger.info(f"Mapped fields: {header_indices}")
        
        # Parse data rows
        products = []
        for row_idx, row in enumerate(all_values[1:], start=2):  # Skip header row
            if not row or all(cell.strip() == '' for cell in row):
                # Skip empty rows
                continue
            
            # Pad row with empty strings if it's shorter than headers
            while len(row) < len(headers):
                row.append('')
            
            product = {}
            for field, col_idx in header_indices.items():
                if col_idx < len(row):
                    product[field] = row[col_idx].strip()
                else:
                    product[field] = ''
            
            # Set defaults for missing required fields
            if 'category' not in product or not product['category']:
                product['category'] = 'Unknown'
            if 'subcategory' not in product or not product['subcategory']:
                product['subcategory'] = 'Unknown'
            if 'quantity' not in product or not product['quantity']:
                product['quantity'] = '1'
            
            # Validate and clean receipt_date
            if 'receipt_date' in product and product['receipt_date']:
                date_str = product['receipt_date'].strip()
                # Check if it looks like a valid date (contains hyphens or slashes)
                if date_str and ('-' in date_str or '/' in date_str):
                    # Try to validate it's actually a date
                    try:
                        # Try to parse common date formats
                        from datetime import datetime
                        # Try various formats
                        for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                            try:
                                datetime.strptime(date_str, date_format)
                                break
                            except ValueError:
                                continue
                        else:
                            # None of the formats worked
                            logger.warning(f"Row {row_idx}: Invalid date format '{date_str}', setting to None")
                            product['receipt_date'] = None
                    except:
                        logger.warning(f"Row {row_idx}: Invalid date '{date_str}', setting to None")
                        product['receipt_date'] = None
                else:
                    # Doesn't look like a date (might be a price or other value)
                    logger.warning(f"Row {row_idx}: Invalid date value '{date_str}' (looks like non-date data), setting to None")
                    product['receipt_date'] = None
            else:
                product['receipt_date'] = None
            
            # Validate that we have at least some data
            if product.get('original_product_name') or product.get('translated_product_name'):
                products.append(product)
            else:
                logger.debug(f"Skipping row {row_idx} - no product name found")
        
        logger.info(f"Successfully read {len(products)} products from Google Sheet")
        return products
        
    except Exception as e:
        logger.error(f"Error reading from Google Sheet: {e}")
        logger.exception("Full error traceback:")
        raise


def upload_to_database(telegram_id: int, products: List[Dict[str, str]]) -> bool:
    """
    Upload products to database
    
    Args:
        telegram_id: Telegram user ID to associate products with
        products: List of product dictionaries
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not products:
            logger.warning("No products to upload")
            return False
        
        logger.info(f"Uploading {len(products)} products for telegram_id: {telegram_id}")
        success = db_service.save_products_to_db(telegram_id, products)
        
        if success:
            logger.info("✅ Successfully uploaded products to database!")
        else:
            logger.error("❌ Failed to upload products to database")
        
        return success
        
    except Exception as e:
        logger.error(f"Error uploading to database: {e}")
        logger.exception("Full error traceback:")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Upload receipt data from Google Sheets to database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --telegram-id 123456789
  %(prog)s --telegram-id 123456789 --spreadsheet-id "abc123xyz" --tab-name "january_2025"
  %(prog)s --telegram-id 123456789 --dry-run
        """
    )
    
    parser.add_argument(
        '--telegram-id',
        type=int,
        required=True,
        help='Telegram user ID to associate the products with'
    )
    
    parser.add_argument(
        '--spreadsheet-id',
        type=str,
        default=config.GOOGLE_SHEETS_SPREADSHEET_ID,
        help='Google Sheets spreadsheet ID (default: from environment variable)'
    )
    
    parser.add_argument(
        '--tab-name',
        type=str,
        default=config.GOOGLE_SHEETS_TAB_NAME,
        help='Tab/sheet name to read from (default: from environment variable or "november_2025")'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Read from Google Sheets but do not upload to database'
    )
    
    args = parser.parse_args()
    
    # Validate required configuration
    if not args.spreadsheet_id:
        logger.error("❌ Error: spreadsheet_id is required. Set GOOGLE_SHEETS_SPREADSHEET_ID in .env or use --spreadsheet-id")
        return 1
    
    if not config.GS_CREDS_PATH.exists():
        logger.error(f"❌ Error: Google Sheets credentials file not found at {config.GS_CREDS_PATH}")
        return 1
    
    try:
        logger.info("=" * 60)
        logger.info("Starting Google Sheets to Database upload")
        logger.info("=" * 60)
        logger.info(f"Telegram ID: {args.telegram_id}")
        logger.info(f"Spreadsheet ID: {args.spreadsheet_id}")
        logger.info(f"Tab Name: {args.tab_name}")
        logger.info(f"Dry Run: {args.dry_run}")
        logger.info("=" * 60)
        
        # Step 1: Read data from Google Sheets
        logger.info("Step 1: Reading data from Google Sheets...")
        products = read_products_from_sheet(args.spreadsheet_id, args.tab_name)
        
        if not products:
            logger.warning("⚠️  No products found in Google Sheet")
            return 0
        
        logger.info(f"Found {len(products)} products")
        
        # Show preview of first few products
        logger.info("\nPreview of products (first 3):")
        for i, product in enumerate(products[:3], 1):
            logger.info(f"  {i}. {product.get('original_product_name', 'N/A')} - "
                       f"{product.get('category', 'N/A')}/{product.get('subcategory', 'N/A')} - "
                       f"{product.get('price', 'N/A')} {product.get('currency', 'N/A')} - "
                       f"Date: {product.get('receipt_date', 'N/A')}")
        
        if args.dry_run:
            logger.info("\n🔍 Dry run mode - skipping database upload")
            logger.info(f"Would upload {len(products)} products for telegram_id {args.telegram_id}")
            return 0
        
        # Step 2: Upload to database
        logger.info("\nStep 2: Uploading to database...")
        success = upload_to_database(args.telegram_id, products)
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✅ Upload completed successfully!")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ Upload failed!")
            logger.error("=" * 60)
            return 1
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Upload cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        logger.exception("Full error traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())


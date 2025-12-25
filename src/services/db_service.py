"""PostgreSQL database service for storing receipt data"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from typing import List, Dict, Optional
from contextlib import contextmanager
from .. import config

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Create and return a database connection
    
    Returns:
        psycopg2.connection: Database connection object
    """
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


@contextmanager
def get_db_cursor():
    """
    Context manager for database cursor
    
    Yields:
        psycopg2.extensions.cursor: Database cursor
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def init_database():
    """
    Initialize database tables (user and products)
    Creates tables if they don't exist
    """
    try:
        with get_db_cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "user" (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    original_product_name VARCHAR(500),
                    translated_product_name VARCHAR(500),
                    category VARCHAR(200),
                    subcategory VARCHAR(200),
                    price DECIMAL(10, 2),
                    receipt_date DATE,
                    currency VARCHAR(10),
                    quantity DECIMAL(10, 2) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on user_id for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id)
            """)
            
            # Create index on telegram_id for faster user lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_telegram_id ON "user"(telegram_id)
            """)
            
            logger.info("Database tables initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.exception("Full error traceback:")
        raise


def get_or_create_user(telegram_id: int) -> int:
    """
    Get user ID by telegram_id, create user if doesn't exist
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        int: User ID in database
    """
    try:
        with get_db_cursor() as cursor:
            # Try to get existing user
            cursor.execute(
                'SELECT id FROM "user" WHERE telegram_id = %s',
                (telegram_id,)
            )
            result = cursor.fetchone()
            
            if result:
                user_id = result['id']
                logger.info(f"Found existing user with telegram_id {telegram_id}, user_id: {user_id}")
                return user_id
            else:
                # Create new user
                cursor.execute(
                    'INSERT INTO "user" (telegram_id) VALUES (%s) RETURNING id',
                    (telegram_id,)
                )
                user_id = cursor.fetchone()['id']
                logger.info(f"Created new user with telegram_id {telegram_id}, user_id: {user_id}")
                return user_id
    except Exception as e:
        logger.error(f"Error getting/creating user: {e}")
        logger.exception("Full error traceback:")
        raise


def save_products_to_db(telegram_id: int, products: List[Dict[str, str]]) -> bool:
    """
    Save products to database
    
    Args:
        telegram_id: Telegram user ID
        products: List of product dictionaries with keys: original_product_name, 
                 translated_product_name, category, subcategory, price, receipt_date, currency, quantity
                 
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get or create user
        user_id = get_or_create_user(telegram_id)
        
        with get_db_cursor() as cursor:
            # Prepare products for insertion
            # Duplicate products based on quantity (same as Google Sheets behavior)
            rows_to_insert = []
            for product in products:
                quantity_str = product.get('quantity', '1')
                try:
                    quantity = float(quantity_str)
                    if quantity < 1:
                        quantity = 1
                except (ValueError, TypeError):
                    quantity = 1
                
                # Create one row per quantity unit
                for _ in range(int(quantity)):
                    # Handle receipt_date - convert empty strings to None
                    receipt_date = product.get('receipt_date')
                    if receipt_date == '' or receipt_date == 'None':
                        receipt_date = None
                    
                    rows_to_insert.append({
                        'user_id': user_id,
                        'original_product_name': product.get('original_product_name', ''),
                        'translated_product_name': product.get('translated_product_name', ''),
                        'category': product.get('category', 'Unknown'),
                        'subcategory': product.get('subcategory', 'Unknown'),
                        'price': product.get('price', '0'),
                        'receipt_date': receipt_date,
                        'currency': product.get('currency', ''),
                        'quantity': quantity
                    })
            
            # Insert products
            if rows_to_insert:
                insert_query = """
                    INSERT INTO products 
                    (user_id, original_product_name, translated_product_name, category, 
                     subcategory, price, receipt_date, currency, quantity)
                    VALUES 
                    (%(user_id)s, %(original_product_name)s, %(translated_product_name)s, 
                     %(category)s, %(subcategory)s, %(price)s, %(receipt_date)s, 
                     %(currency)s, %(quantity)s)
                """
                cursor.executemany(insert_query, rows_to_insert)
                logger.info(f"Successfully saved {len(rows_to_insert)} product rows to database (from {len(products)} products with quantities)")
                return True
            else:
                logger.warning("No products to save to database")
                return False
                
    except Exception as e:
        logger.error(f"Error saving products to database: {e}")
        logger.exception("Full error traceback:")
        return False


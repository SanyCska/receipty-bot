#!/usr/bin/env python3
"""Database initialization script for Receipty Bot"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import db_service

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database tables"""
    try:
        logger.info("Initializing database tables...")
        db_service.init_database()
        logger.info("✅ Database initialized successfully!")
        logger.info("Tables created:")
        logger.info("  - user (with telegram_id)")
        logger.info("  - products (with connection to user)")
        return 0
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        logger.exception("Full error traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())


"""Configuration constants and settings"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File paths
RECEIPT_CATEGORIES_PATH = Path('receipt_categories.csv')
CSV_OUTPUT_DIR = Path('receipts_csv')
CSV_OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# OpenAI Settings
OPENAI_MODEL = "gpt-4o"
OPENAI_MAX_TOKENS = 4000

# Media Group Settings
MEDIA_GROUP_MAX_WAIT_TIME = 3.0  # seconds
MEDIA_GROUP_CHECK_INTERVAL = 0.5  # seconds
MEDIA_GROUP_IDLE_THRESHOLD = 1.0  # seconds

# Telegram Message Settings
MAX_MESSAGE_LENGTH = 4000  # Telegram message limit


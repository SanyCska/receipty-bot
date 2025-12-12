"""Configuration constants and settings"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

# File paths
RECEIPT_CATEGORIES_PATH = PROJECT_ROOT / 'data' / 'receipt_categories.csv'
CSV_OUTPUT_DIR = PROJECT_ROOT / 'output' / 'receipts_csv'
CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Google Sheets credentials path
GS_CREDS_PATH = PROJECT_ROOT / 'config' / 'gs_creds.json'

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

# Google Sheets Settings
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
GOOGLE_SHEETS_TAB_NAME = os.getenv('GOOGLE_SHEETS_TAB_NAME', 'november_2025')

# Database Settings
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'receipty_bot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')


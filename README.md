# Receipt Processing Telegram Bot

A Telegram bot that processes supermarket receipt photos using OpenAI's GPT-4o vision API to extract and categorize products.

## Project Structure

```
receipty-bot/
├── main.py                    # Main entry point
├── src/                       # Source code package
│   ├── bot.py                 # Main bot application and handlers
│   ├── config.py              # Configuration constants and settings
│   ├── prompts.py             # Prompt templates and category loading
│   ├── services/              # API service integrations
│   │   ├── openai_service.py  # OpenAI API interactions
│   │   └── gs_service.py      # Google Sheets integration
│   └── utils/                 # Utility modules
│       ├── csv_parser.py      # CSV extraction and parsing utilities
│       ├── formatters.py      # Message formatting utilities
│       └── telegram_utils.py  # Telegram bot utilities
├── data/                      # Data files
│   └── receipt_categories.csv # Product categories reference
├── config/                    # Configuration files
│   └── gs_creds.json          # Google Sheets credentials
├── output/                    # Output files
│   └── receipts_csv/          # Generated receipt CSV files
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

### Module Descriptions

- **`main.py`**: Main entry point that starts the bot
- **`src/bot.py`**: Telegram bot handlers, media group processing, and main application logic
- **`src/config.py`**: All configuration constants, paths, and settings
- **`src/services/openai_service.py`**: OpenAI API client, image processing, and receipt analysis
- **`src/services/gs_service.py`**: Google Sheets integration for saving receipt data
- **`src/utils/csv_parser.py`**: Functions for extracting CSV from API responses and parsing CSV data
- **`src/utils/formatters.py`**: Message formatting for user-friendly output
- **`src/utils/telegram_utils.py`**: Telegram-specific utilities like photo downloading
- **`src/prompts.py`**: Prompt templates and category CSV loading

## Features

- 📸 Upload receipt photos via Telegram
- 🤖 AI-powered receipt analysis using OpenAI GPT-4o
- 📊 Automatic product categorization based on CSV reference
- 🌍 Product name translation to Russian
- 💰 Price extraction and validation
- 📈 Optional Google Sheets integration for data storage

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a Telegram bot:**
   - Talk to [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the bot token

3. **Get OpenAI API key:**
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Create an API key in your dashboard

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` (or create a `.env` file)
   - Add your Telegram bot token and OpenAI API key:
     ```
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
     OPENAI_API_KEY=your_openai_api_key_here
     GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here  # Optional
     GOOGLE_SHEETS_TAB_NAME=november_2025  # Optional, defaults to november_2025
     ```

5. **Set up Google Sheets integration (Optional):**
   - If you want to save receipt data to Google Sheets:
     1. Go to [Google Cloud Console](https://console.cloud.google.com/)
     2. Create a new project or select an existing one
     3. Enable the Google Sheets API and Google Drive API
     4. Create a Service Account:
        - Go to "IAM & Admin" → "Service Accounts"
        - Click "Create Service Account"
        - Give it a name and click "Create and Continue"
        - Skip role assignment and click "Done"
     5. Create credentials:
        - Click on the created service account
        - Go to "Keys" tab → "Add Key" → "Create new key"
        - Select JSON format and download
     6. Save the downloaded JSON file as `config/gs_creds.json`
     7. Share your Google Sheet with the service account email (found in the JSON file)
     8. Add `GOOGLE_SHEETS_SPREADSHEET_ID` to your `.env` file with your spreadsheet ID
   - **Note:** If you skip this step, the bot will still work but won't save data to Google Sheets

## Usage

1. **Start the bot:**
   ```bash
   python main.py
   ```

2. **Use the bot:**
   - Open Telegram and find your bot
   - Send `/start` to begin
   - Upload one or more receipt photos
   - Wait for the bot to process and return categorized product information

## How it works

1. User uploads receipt photo(s) to the bot
2. Bot downloads the photo(s)
3. Photo(s) are sent to OpenAI GPT-4o with a detailed prompt
4. OpenAI extracts products, prices, and categorizes them
5. Bot formats the response and sends it back to the user
6. All CSV responses from OpenAI are saved to `output/receipts_csv/` folder with timestamps
7. If Google Sheets is configured, data is automatically saved to the specified spreadsheet
8. Full API responses are logged for debugging

## Categories

Product categories are defined in `receipt_categories.csv` with the following structure:
- `category_group`: Main category (e.g., Food & Groceries, Beverages)
- `subcategory`: Specific subcategory (e.g., Fresh Meat, Water)

## Notes

- The bot uses GPT-4o for vision processing
- Products are automatically categorized using the CSV reference
- Product names are translated to Russian
- Prices are validated against receipt totals
- All OpenAI API responses are logged with details (model, usage, response length)
- CSV responses are automatically saved to `output/receipts_csv/` folder with timestamp filenames (e.g., `receipt_20241225_143022_123456.csv`)


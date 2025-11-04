# Receipt Processing Telegram Bot

A Telegram bot that processes supermarket receipt photos using OpenAI's GPT-4o vision API to extract and categorize products.

## Project Structure

```
receipty-bot/
├── bot.py              # Main bot application and handlers
├── config.py           # Configuration constants and settings
├── csv_parser.py       # CSV extraction and parsing utilities
├── openai_service.py   # OpenAI API interactions
├── prompts.py          # Prompt templates and category loading
├── formatters.py       # Message formatting utilities
├── telegram_utils.py   # Telegram bot utilities
├── receipt_categories.csv  # Product categories reference
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

### Module Descriptions

- **`bot.py`**: Main entry point, Telegram bot handlers, and media group processing
- **`config.py`**: All configuration constants, paths, and settings
- **`csv_parser.py`**: Functions for extracting CSV from API responses and parsing CSV data
- **`openai_service.py`**: OpenAI API client, image processing, and receipt analysis
- **`prompts.py`**: Prompt templates and category CSV loading
- **`formatters.py`**: Message formatting for user-friendly output
- **`telegram_utils.py`**: Telegram-specific utilities like photo downloading

## Features

- 📸 Upload receipt photos via Telegram
- 🤖 AI-powered receipt analysis using OpenAI GPT-4o
- 📊 Automatic product categorization based on CSV reference
- 🌍 Product name translation to Russian
- 💰 Price extraction and validation

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
   - Copy `.env.example` to `.env`
   - Add your Telegram bot token and OpenAI API key:
     ```
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
     OPENAI_API_KEY=your_openai_api_key_here
     ```

## Usage

1. **Start the bot:**
   ```bash
   python bot.py
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
6. All CSV responses from OpenAI are saved to `receipts_csv/` folder with timestamps
7. Full API responses are logged for debugging

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
- CSV responses are automatically saved to `receipts_csv/` folder with timestamp filenames (e.g., `receipt_20241225_143022_123456.csv`)


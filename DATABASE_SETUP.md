# Database Setup Instructions

## Overview

The bot now supports PostgreSQL database storage in addition to Google Sheets. Products are saved to both locations (if configured).

## Database Schema

The database has two tables:

### 1. `user` table
- `id` (SERIAL PRIMARY KEY): Auto-incrementing user ID
- `telegram_id` (BIGINT UNIQUE NOT NULL): Telegram user ID
- `created_at` (TIMESTAMP): When the user was created
- `updated_at` (TIMESTAMP): Last update time

### 2. `products` table
- `id` (SERIAL PRIMARY KEY): Auto-incrementing product ID
- `user_id` (INTEGER NOT NULL): Foreign key to `user.id`
- `original_product_name` (VARCHAR(500)): Original product name from receipt
- `translated_product_name` (VARCHAR(500)): Translated product name
- `category` (VARCHAR(200)): Product category
- `subcategory` (VARCHAR(200)): Product subcategory
- `price` (DECIMAL(10, 2)): Product price
- `receipt_date` (DATE): Date of the receipt
- `currency` (VARCHAR(10)): Currency code (e.g., USD, EUR)
- `quantity` (DECIMAL(10, 2)): Product quantity
- `created_at` (TIMESTAMP): When the product was saved
- `updated_at` (TIMESTAMP): Last update time

## Initialization Steps

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download and install from [PostgreSQL website](https://www.postgresql.org/download/windows/)

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE receipty_bot;

# Exit psql
\q
```

Or using command line:
```bash
createdb -U postgres receipty_bot
```

### 3. Configure Environment Variables

Add these to your `.env` file:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=receipty_bot
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 4. Initialize Database Tables

Run the initialization script:

```bash
python init_db.py
```

This will create:
- `user` table with telegram_id
- `products` table with all product fields
- Indexes on `user_id` and `telegram_id` for faster queries
- Foreign key relationship between products and users

### 5. Verify Setup

You can verify the tables were created:

```bash
psql -U postgres -d receipty_bot -c "\dt"
```

You should see both `user` and `products` tables.

## How It Works

1. When a user sends a receipt, the bot extracts products
2. The bot gets or creates a user record using the Telegram ID
3. Products are saved to the database with a foreign key to the user
4. Products are also saved to Google Sheets (if configured)
5. Each product row is duplicated based on quantity (same behavior as Google Sheets)

## Notes

- The database connection is automatically managed with connection pooling
- Users are automatically created when they first send a receipt
- Products are linked to users via `user_id` foreign key
- The database and Google Sheets work independently - if one fails, the other still works
- All database operations are logged for debugging


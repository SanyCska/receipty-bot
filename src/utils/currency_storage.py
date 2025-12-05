"""Currency storage and management utilities"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from .. import config

logger = logging.getLogger(__name__)

# Path to currency preferences file
CURRENCY_STORAGE_PATH = config.PROJECT_ROOT / 'data' / 'currency_preferences.json'

# Default currencies
DEFAULT_CURRENCIES = ['RSD', 'EUR', 'USD', 'RUB']
MAX_STORED_CURRENCIES = 6

# Currency code to symbol mapping
CURRENCY_SYMBOLS = {
    'RSD': 'дин.',  # Serbian Dinar
    'EUR': '€',
    'USD': '$',
    'RUB': '₽',
    'GBP': '£',
    'JPY': '¥',
    'CNY': '¥',
    'CHF': 'CHF',
    'CAD': 'C$',
    'AUD': 'A$',
    'NZD': 'NZ$',
    'SEK': 'kr',
    'NOK': 'kr',
    'DKK': 'kr',
    'PLN': 'zł',
    'CZK': 'Kč',
    'HUF': 'Ft',
    'RON': 'lei',
    'BGN': 'лв',
    'HRK': 'kn',
    'TRY': '₺',
    'INR': '₹',
    'KRW': '₩',
    'SGD': 'S$',
    'HKD': 'HK$',
    'MXN': '$',
    'BRL': 'R$',
    'ZAR': 'R',
}


def get_currency_symbol(currency_code: str) -> str:
    """
    Get currency symbol for a currency code
    
    Args:
        currency_code: Three-letter currency code (e.g., 'USD', 'EUR')
    
    Returns:
        Currency symbol (e.g., '$', '€') or the currency code if symbol not found
    """
    currency_code = currency_code.upper().strip()
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)


def load_currency_preferences() -> Dict[int, Dict]:
    """
    Load currency preferences from file
    
    Returns:
        Dictionary mapping user_id to preferences dict with 'currencies' list
    """
    try:
        if CURRENCY_STORAGE_PATH.exists():
            with open(CURRENCY_STORAGE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys to int (JSON keys are always strings)
                result = {}
                for key, value in data.items():
                    try:
                        result[int(key)] = value
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid user_id in preferences: {key}")
                logger.info(f"Loaded currency preferences for {len(result)} users")
                return result
        else:
            logger.info("Currency preferences file not found, starting fresh")
            return {}
    except Exception as e:
        logger.error(f"Error loading currency preferences: {e}")
        return {}


def save_currency_preferences(preferences: Dict[int, Dict]):
    """Save currency preferences to file"""
    try:
        # Ensure directory exists
        CURRENCY_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert int keys to strings for JSON (JSON requires string keys)
        data_to_save = {str(key): value for key, value in preferences.items()}
        
        with open(CURRENCY_STORAGE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        logger.info("Saved currency preferences")
    except Exception as e:
        logger.error(f"Error saving currency preferences: {e}")
        raise


def get_user_currencies(user_id: int) -> List[str]:
    """
    Get list of currencies for a user, with last used first
    
    Returns:
        List of currency codes, with last used first, then defaults
    """
    preferences = load_currency_preferences()
    user_prefs = preferences.get(user_id, {})
    user_currencies = user_prefs.get('currencies', [])
    
    # Combine user currencies with defaults, removing duplicates
    result = []
    seen = set()
    
    # Add user currencies first (last used is first)
    for currency in user_currencies:
        if currency.upper() not in seen:
            result.append(currency.upper())
            seen.add(currency.upper())
    
    # Add default currencies that aren't already in the list
    for currency in DEFAULT_CURRENCIES:
        if currency.upper() not in seen:
            result.append(currency.upper())
            seen.add(currency.upper())
    
    return result


def add_user_currency(user_id: int, currency: str):
    """
    Add currency to user's preference list, moving it to the front
    
    Args:
        user_id: Telegram user ID
        currency: Currency code (3 letters)
    """
    currency = currency.upper().strip()
    
    if len(currency) != 3:
        logger.warning(f"Invalid currency code: {currency}")
        return
    
    preferences = load_currency_preferences()
    
    if user_id not in preferences:
        preferences[user_id] = {'currencies': []}
    
    user_currencies = preferences[user_id]['currencies']
    
    # Remove currency if it exists (to move it to front)
    if currency in user_currencies:
        user_currencies.remove(currency)
    
    # Add to front
    user_currencies.insert(0, currency)
    
    # Keep only last MAX_STORED_CURRENCIES
    preferences[user_id]['currencies'] = user_currencies[:MAX_STORED_CURRENCIES]
    
    save_currency_preferences(preferences)
    logger.info(f"Added currency {currency} for user {user_id}")


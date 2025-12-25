"""Language storage and management utilities"""
import json
import logging
from pathlib import Path
from typing import List, Dict
from .. import config

logger = logging.getLogger(__name__)

# Path to language preferences file
LANGUAGE_STORAGE_PATH = config.PROJECT_ROOT / 'data' / 'language_preferences.json'

# Default languages
DEFAULT_LANGUAGES = ['Serbian', 'English', 'Russian', 'German', 'French', 'Spanish']
MAX_STORED_LANGUAGES = 6


def load_language_preferences() -> Dict[int, Dict]:
    """
    Load language preferences from file
    
    Returns:
        Dictionary mapping user_id to preferences dict with 'languages' list
    """
    try:
        if LANGUAGE_STORAGE_PATH.exists():
            with open(LANGUAGE_STORAGE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys to int (JSON keys are always strings)
                result = {}
                for key, value in data.items():
                    try:
                        result[int(key)] = value
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid user_id in preferences: {key}")
                logger.info(f"Loaded language preferences for {len(result)} users")
                return result
        else:
            logger.info("Language preferences file not found, starting fresh")
            return {}
    except Exception as e:
        logger.error(f"Error loading language preferences: {e}")
        return {}


def save_language_preferences(preferences: Dict[int, Dict]):
    """Save language preferences to file"""
    try:
        # Ensure directory exists
        LANGUAGE_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert int keys to strings for JSON (JSON requires string keys)
        data_to_save = {str(key): value for key, value in preferences.items()}
        
        with open(LANGUAGE_STORAGE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        logger.info("Saved language preferences")
    except Exception as e:
        logger.error(f"Error saving language preferences: {e}")
        raise


def get_user_languages(user_id: int) -> List[str]:
    """
    Get list of languages for a user, with last used first
    
    Returns:
        List of language names, with last used first, then defaults
    """
    preferences = load_language_preferences()
    user_prefs = preferences.get(user_id, {})
    user_languages = user_prefs.get('languages', [])
    
    # Combine user languages with defaults, removing duplicates
    result = []
    seen = set()
    
    # Add user languages first (last used is first)
    for language in user_languages:
        if language not in seen:
            result.append(language)
            seen.add(language)
    
    # Add default languages that aren't already in the list
    for language in DEFAULT_LANGUAGES:
        if language not in seen:
            result.append(language)
            seen.add(language)
    
    return result


def add_user_language(user_id: int, language: str):
    """
    Add language to user's preference list, moving it to the front
    
    Args:
        user_id: Telegram user ID
        language: Language name (e.g., 'Serbian', 'English')
    """
    language = language.strip()
    
    if not language:
        logger.warning(f"Empty language provided for user {user_id}")
        return
    
    preferences = load_language_preferences()
    
    if user_id not in preferences:
        preferences[user_id] = {'languages': []}
    
    user_languages = preferences[user_id]['languages']
    
    # Remove language if it exists (to move it to front)
    if language in user_languages:
        user_languages.remove(language)
    
    # Add to front
    user_languages.insert(0, language)
    
    # Keep only last MAX_STORED_LANGUAGES
    preferences[user_id]['languages'] = user_languages[:MAX_STORED_LANGUAGES]
    
    save_language_preferences(preferences)
    logger.info(f"Added language {language} for user {user_id}")





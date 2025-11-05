"""Telegram bot utilities"""
import logging
from typing import Dict
from telegram import Update
from telegram.ext import ContextTypes
from .. import config

logger = logging.getLogger(__name__)

# Store media groups for processing
# Key: media_group_id, Value: dict with 'photos' list and 'last_update' timestamp
media_groups: Dict[str, Dict] = {}


async def download_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bytes:
    """Download photo from Telegram message"""
    photo = update.message.photo[-1]  # Get highest resolution photo
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    photo_bytes = bytes(photo_bytes)
    
    # Validate image
    if len(photo_bytes) == 0:
        raise ValueError("Downloaded photo is empty")
    
    logger.info(f"Downloaded photo: {len(photo_bytes)} bytes, file_id={photo.file_id}")
    
    return photo_bytes


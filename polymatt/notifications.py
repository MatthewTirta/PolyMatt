"""
notifications.py — Send Telegram messages when important things happen.

If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID are not set in .env,
all notifications are silently skipped — the bot keeps running normally.
"""
import logging
import requests
from polymatt import config

logger = logging.getLogger(__name__)


def send(message: str):
    """
    Send a message to your Telegram chat.
    Does nothing (no error) if Telegram is not configured.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return  # silently skip

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
        }, timeout=10)
        if not resp.ok:
            logger.warning("Telegram send failed: %s", resp.text)
    except Exception as e:
        logger.warning("Telegram error (non-fatal): %s", e)

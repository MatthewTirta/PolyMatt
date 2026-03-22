"""
btc_price.py — Fetch BTC spot price from CoinGecko and store it.

Uses CoinGecko's free public API — no API key required.
Call start_collection() to begin polling every 60 seconds.
"""
import asyncio
import logging
import requests
from datetime import datetime
from polymatt.data.storage import save_btc_price

logger = logging.getLogger(__name__)
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
POLL_INTERVAL_SECONDS = 60


def fetch_btc_price() -> float:
    """Fetch the current BTC/USD price from CoinGecko. Returns 0.0 on failure."""
    try:
        resp = requests.get(COINGECKO_URL, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["bitcoin"]["usd"])
    except Exception as e:
        logger.warning("BTC price fetch failed (non-fatal): %s", e)
        return 0.0


async def start_collection(stop_event: asyncio.Event):
    """Poll CoinGecko every 60 seconds and save each price to SQLite."""
    logger.info("BTC price collection started (every %ds)", POLL_INTERVAL_SECONDS)
    while not stop_event.is_set():
        price = fetch_btc_price()
        if price > 0:
            save_btc_price(datetime.utcnow(), price)
            logger.debug("BTC price saved: $%.2f", price)
        else:
            logger.warning("BTC price fetch returned 0 — skipping save this cycle")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

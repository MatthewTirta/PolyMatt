"""
client.py — Connects to the Polymarket CLOB API.

All network calls go through _with_retry(), which automatically
retries up to 3 times if something goes wrong.
"""
import time
import logging
from py_clob_client.client import ClobClient
from polymatt import config

logger = logging.getLogger(__name__)

# Seconds to wait before each retry attempt
RETRY_DELAYS = [1, 2, 4]


def _with_retry(func, *args, **kwargs):
    """
    Call func(*args, **kwargs). If it raises an exception,
    wait and try again up to 3 times total.
    """
    last_error = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < len(RETRY_DELAYS):
                logger.warning("Attempt %d failed: %s. Retrying in %ds...", attempt, e, delay)
                time.sleep(delay)
            else:
                logger.warning("Attempt %d failed: %s. Giving up.", attempt, e)
    raise last_error


def get_client() -> ClobClient:
    """
    Create a Polymarket API client.
    - If API keys are in .env: authenticated (can place orders later)
    - If no keys: read-only mode (fine for Phase 1 research)
    """
    if config.POLYMARKET_API_KEY:
        return ClobClient(
            host=config.POLYMARKET_HOST,
            key=config.POLYMARKET_PRIVATE_KEY,
            chain_id=137,  # Polygon mainnet
            creds={
                "apiKey": config.POLYMARKET_API_KEY,
                "secret": config.POLYMARKET_API_SECRET,
                "passphrase": config.POLYMARKET_API_PASSPHRASE,
            },
        )
    return ClobClient(host=config.POLYMARKET_HOST)


def fetch_markets(client: ClobClient) -> list:
    """Fetch all active markets from Polymarket."""
    return _with_retry(client.get_markets)


def fetch_orderbook(client: ClobClient, condition_id: str) -> dict:
    """Fetch the current orderbook for one market."""
    return _with_retry(client.get_order_book, condition_id)

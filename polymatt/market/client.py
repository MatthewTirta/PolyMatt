"""
client.py — Connects to the Polymarket CLOB API and Gamma search API.

All network calls go through _with_retry(), which automatically
retries up to 3 times if something goes wrong.
"""
import time
import logging
import requests
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
    """Fetch all active markets from Polymarket. Returns the list from the 'data' key."""
    result = _with_retry(client.get_markets)
    # API returns {"data": [...], "next_cursor": ..., "count": ...}
    if isinstance(result, dict):
        return result.get("data", [])
    return result or []


def fetch_orderbook(client: ClobClient, token_id: str) -> dict:
    """
    Fetch the current orderbook for one market outcome.

    The CLOB API identifies orderbooks by token_id (one per outcome),
    NOT by condition_id.  Pass Market.token_ids[0] for the Up/Yes side.

    Uses a direct HTTP request because py_clob_client's get_order_book()
    rejects the large integer token IDs that Polymarket uses for 5-minute
    direction markets.
    """
    url = f"{config.POLYMARKET_HOST}/book?token_id={token_id}"

    def _fetch():
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    return _with_retry(_fetch)


# ── Gamma API (market search / discovery) ────────────────────────────────────
GAMMA_API = "https://gamma-api.polymarket.com/markets"


def fetch_gamma_btc_direction_markets(limit: int = 20) -> list:
    """
    Use Polymarket's Gamma search API to find active BTC 'Up or Down' markets.

    These are the 5-minute direction markets that are not surfaced by the
    CLOB API's get_markets() endpoint.  The Gamma API returns richer metadata
    (bestBid, bestAsk, volume24hr, outcomes) in a single call.

    Returns a list of raw dicts from the Gamma API.
    """
    try:
        resp = requests.get(
            GAMMA_API,
            params={
                "active": "true",
                "closed": "false",
                "order": "startDate",
                "ascending": "false",
                "limit": limit,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        # Keep only Bitcoin Up or Down markets
        return [
            m for m in data
            if "bitcoin up or down" in m.get("question", "").lower()
        ]
    except Exception as e:
        logger.warning("Gamma API request failed: %s", e)
        return []

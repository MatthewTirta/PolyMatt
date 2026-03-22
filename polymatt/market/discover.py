"""
discover.py — Find BTC-related markets on Polymarket.

Fetches all markets and filters to ones whose question mentions BTC or Bitcoin.
"""
import logging
from polymatt.market.client import get_client, fetch_markets
from polymatt.market.models import Market

logger = logging.getLogger(__name__)

# Words that identify a BTC market question (case-insensitive)
BTC_KEYWORDS = ["btc", "bitcoin"]


def is_btc_market(question: str) -> bool:
    """Return True if the market question is about BTC."""
    lower = question.lower()
    return any(kw in lower for kw in BTC_KEYWORDS)


def get_btc_markets() -> list:
    """
    Fetch all active markets and return only BTC-related ones.
    Returns a list of Market objects.
    """
    client = get_client()
    raw = fetch_markets(client)

    btc = []
    for m in raw:
        question = m.get("question", "")
        if not is_btc_market(question):
            continue
        # Prices live in the tokens list: [{outcome: "Yes", price: 0.6}, {outcome: "No", price: 0.4}]
        tokens = m.get("tokens", [])
        yes_price = next((float(t["price"]) for t in tokens if t.get("outcome") == "Yes"), 0.0)
        no_price = next((float(t["price"]) for t in tokens if t.get("outcome") == "No"), 0.0)
        btc.append(Market(
            condition_id=m.get("condition_id", ""),
            question=question,
            yes_price=yes_price,
            no_price=no_price,
            volume_usd=float(m.get("volume") or 0),
            end_date=m.get("end_date_iso"),
            active=m.get("active", False),
        ))

    logger.info("Found %d BTC markets (out of %d total)", len(btc), len(raw))
    return btc

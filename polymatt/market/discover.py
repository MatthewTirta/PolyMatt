"""
discover.py — Find BTC-related markets on Polymarket.

Primary path: Gamma API → "Bitcoin Up or Down" 5-minute direction markets.
Fallback path: CLOB API → any market whose question mentions BTC/Bitcoin.
"""
import json
import logging
from polymatt.market.client import (
    get_client,
    fetch_markets,
    fetch_gamma_btc_direction_markets,
)
from polymatt.market.models import Market

logger = logging.getLogger(__name__)

# Words that identify a BTC market question (case-insensitive)
BTC_KEYWORDS = ["btc", "bitcoin"]


def is_btc_market(question: str) -> bool:
    """Return True if the market question is about BTC."""
    lower = question.lower()
    return any(kw in lower for kw in BTC_KEYWORDS)


def _gamma_to_market(m: dict) -> Market:
    """
    Convert a Gamma API market dict to a Market object.

    Gamma uses outcomes=["Up","Down"] and outcomePrices=["0.5","0.5"].
    We map Up → yes_price, Down → no_price to stay compatible with the
    rest of the codebase (YES = bet it goes up).
    """
    outcomes = m.get("outcomes", [])
    prices_raw = m.get("outcomePrices", [])

    # Build a lookup: outcome name → price
    price_map = {}
    for i, outcome in enumerate(outcomes):
        try:
            price_map[outcome] = float(prices_raw[i])
        except (IndexError, ValueError, TypeError):
            price_map[outcome] = 0.0

    # Fall back to bestBid/bestAsk if outcomePrices is missing
    up_price = price_map.get("Up", float(m.get("bestBid") or 0))
    down_price = price_map.get("Down", float(m.get("bestAsk") or 0))

    # clobTokenIds comes as a JSON string from the Gamma API, e.g. '["123...", "456..."]'
    raw_ids = m.get("clobTokenIds", [])
    if isinstance(raw_ids, str):
        try:
            token_ids = json.loads(raw_ids)
        except (json.JSONDecodeError, ValueError):
            token_ids = []
    else:
        token_ids = list(raw_ids)

    return Market(
        condition_id=m.get("conditionId", ""),
        question=m.get("question", ""),
        yes_price=up_price,    # "Up" maps to yes_price
        no_price=down_price,   # "Down" maps to no_price
        volume_usd=float(m.get("volume24hr") or 0),
        end_date=m.get("endDate"),
        active=m.get("active", False),
        token_ids=token_ids,
    )


def get_btc_markets() -> list:
    """
    Return BTC direction markets, preferring the Gamma API.

    1. Try Gamma API first — returns the live 5-minute "Bitcoin Up or Down"
       markets with real volume and prices.
    2. Fall back to CLOB API if Gamma returns nothing (e.g. API outage).

    Returns a list of Market objects.
    """
    # ── Primary: Gamma API ────────────────────────────────────────────────
    gamma_raw = fetch_gamma_btc_direction_markets(limit=20)
    if gamma_raw:
        markets = [_gamma_to_market(m) for m in gamma_raw]
        logger.info("Found %d BTC direction markets via Gamma API", len(markets))
        return markets

    # ── Fallback: CLOB API ────────────────────────────────────────────────
    logger.warning("Gamma API returned nothing — falling back to CLOB API")
    client = get_client()
    raw = fetch_markets(client)

    btc = []
    for m in raw:
        question = m.get("question", "")
        if not is_btc_market(question):
            continue
        tokens = m.get("tokens", [])
        yes_price = next(
            (float(t["price"]) for t in tokens if t.get("outcome") == "Yes"), 0.0
        )
        no_price = next(
            (float(t["price"]) for t in tokens if t.get("outcome") == "No"), 0.0
        )
        btc.append(Market(
            condition_id=m.get("condition_id", ""),
            question=question,
            yes_price=yes_price,
            no_price=no_price,
            volume_usd=float(m.get("volume") or 0),
            end_date=m.get("end_date_iso"),
            active=m.get("active", False),
        ))

    logger.info("Found %d BTC markets via CLOB fallback (out of %d total)", len(btc), len(raw))
    return btc

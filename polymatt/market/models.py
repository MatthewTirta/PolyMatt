"""
models.py — Data structures used everywhere in PolyMatt.

These are just containers for data — no business logic lives here.
Think of them like labelled boxes: Market holds market info,
Trade holds one completed trade, etc.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Market:
    """One Polymarket prediction market (e.g. 'Will BTC close above $70k?')."""
    condition_id: str       # unique ID used in all API calls
    question: str           # the market question in plain English
    yes_price: float        # current price of a YES share (0.0 = 0%, 1.0 = 100%)
    no_price: float         # current price of a NO share
    volume_usd: float       # total USD traded in this market
    end_date: Optional[str] # when the market resolves (ISO date string)
    active: bool = True     # False if the market is closed


@dataclass
class OrderbookLevel:
    """One row in the order book — a price and the amount available at that price."""
    price: float
    size: float


@dataclass
class Orderbook:
    """Snapshot of all buy and sell orders for one market at one moment in time."""
    condition_id: str
    timestamp: datetime
    bids: list = field(default_factory=list)  # buy orders (list of OrderbookLevel)
    asks: list = field(default_factory=list)  # sell orders (list of OrderbookLevel)

    def best_bid(self) -> Optional[float]:
        """Highest price a buyer is willing to pay."""
        return max((b.price for b in self.bids), default=None)

    def best_ask(self) -> Optional[float]:
        """Lowest price a seller is willing to accept."""
        return min((a.price for a in self.asks), default=None)

    def spread_pct(self) -> Optional[float]:
        """Gap between best bid and ask, as a % of the mid price."""
        bid, ask = self.best_bid(), self.best_ask()
        if bid is None or ask is None or bid == 0:
            return None
        mid = (bid + ask) / 2
        return ((ask - bid) / mid) * 100


@dataclass
class Trade:
    """One completed trade on Polymarket."""
    condition_id: str
    timestamp: datetime
    price: float
    size: float
    side: str  # "YES" or "NO"


@dataclass
class Signal:
    """A trading signal produced by the strategy — 'I think you should buy YES here'."""
    condition_id: str
    direction: str    # "YES" or "NO"
    confidence: float # 0.0 to 1.0 — how strong the signal is
    reason: str       # plain English explanation, e.g. "BTC +2.3% in 5min, odds unchanged"


@dataclass
class PaperTrade:
    """A simulated trade — tracks entry, exit, and profit/loss."""
    condition_id: str
    direction: str
    entry_price: float
    size_usd: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None   # positive = profit, negative = loss
    reason: str = ""

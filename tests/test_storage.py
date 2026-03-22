# tests/test_storage.py
from datetime import datetime, timedelta
from polymatt.market.models import Trade, Orderbook, OrderbookLevel
import polymatt.data.storage as storage


def test_save_and_retrieve_trade(tmp_path, monkeypatch):
    """Save a trade and confirm it can be retrieved."""
    # Point storage at a temporary DB so we don't touch data/polymatt.db
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()

    trade = Trade("cond-1", datetime.utcnow(), price=0.65, size=10.0, side="YES")
    storage.save_trade(trade)
    since = datetime.utcnow() - timedelta(seconds=5)
    results = storage.get_trades_since("cond-1", since)
    assert len(results) == 1
    assert results[0].price == 0.65


def test_trade_count_last_hour(tmp_path, monkeypatch):
    """Count of trades in the last hour should reflect all saved trades."""
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()

    for _ in range(5):
        storage.save_trade(Trade("cond-2", datetime.utcnow(), 0.5, 10.0, "YES"))
    count = storage.get_trade_count_last_hour("cond-2")
    assert count == 5


def test_save_and_retrieve_orderbook(tmp_path, monkeypatch):
    """Save an orderbook snapshot and confirm bids/asks round-trip correctly."""
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()

    ob = Orderbook("cond-3", datetime.utcnow(),
                   bids=[OrderbookLevel(0.49, 100)],
                   asks=[OrderbookLevel(0.51, 100)])
    storage.save_orderbook(ob)
    since = datetime.utcnow() - timedelta(seconds=5)
    results = storage.get_orderbooks_since("cond-3", since)
    assert len(results) == 1
    assert results[0].best_bid() == 0.49

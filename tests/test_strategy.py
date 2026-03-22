# tests/test_strategy.py
from datetime import datetime, timedelta
from polymatt.market.models import Trade, Orderbook, OrderbookLevel
from polymatt.strategy.baseline import StrategyParams, evaluate_signal, validate_lag_hypothesis


def make_trades(prices: list, minutes_apart: int = 1) -> list:
    """Helper: build a list of Trade objects from a price list."""
    now = datetime.utcnow()
    return [
        Trade(
            condition_id="test",
            timestamp=now - timedelta(minutes=(len(prices) - i) * minutes_apart),
            price=p, size=10.0, side="YES",
        )
        for i, p in enumerate(prices)
    ]


def test_no_signal_when_momentum_below_threshold():
    """Flat prices should produce no signal."""
    params = StrategyParams()
    trades = make_trades([0.50, 0.50, 0.50, 0.50, 0.50])
    ob = Orderbook("test", datetime.utcnow(),
                   bids=[OrderbookLevel(0.49, 100)],
                   asks=[OrderbookLevel(0.51, 100)])
    signal = evaluate_signal("test", trades, ob, btc_change_pct=0.1, params=params)
    assert signal is None


def test_buy_signal_on_strong_btc_move():
    """BTC +3% with unchanged odds should produce a YES signal."""
    params = StrategyParams()
    trades = make_trades([0.50, 0.50, 0.50, 0.50, 0.50])
    ob = Orderbook("test", datetime.utcnow(),
                   bids=[OrderbookLevel(0.49, 1000)],
                   asks=[OrderbookLevel(0.51, 1000)])
    signal = evaluate_signal("test", trades, ob, btc_change_pct=3.0, params=params)
    assert signal is not None
    assert signal.direction == "YES"
    assert len(signal.reason) > 0  # must have a plain-English reason


def test_signal_reason_contains_btc_change():
    """The reason string must mention the BTC price change."""
    params = StrategyParams()
    trades = make_trades([0.50] * 5)
    ob = Orderbook("test", datetime.utcnow(),
                   bids=[OrderbookLevel(0.49, 1000)],
                   asks=[OrderbookLevel(0.51, 1000)])
    signal = evaluate_signal("test", trades, ob, btc_change_pct=3.0, params=params)
    assert "3.0%" in signal.reason or "BTC" in signal.reason

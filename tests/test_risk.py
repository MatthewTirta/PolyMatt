# tests/test_risk.py
import pytest
from unittest.mock import patch
from polymatt.paper_trader.risk import RiskChecker


def make_checker(**overrides):
    """Helper: create a RiskChecker with test-friendly defaults."""
    defaults = dict(
        bankroll=1000.0,
        max_risk_per_trade_pct=2.0,
        max_daily_loss_pct=10.0,
        max_concurrent_positions=3,
        min_liquidity_usd=500.0,
        max_spread_pct=5.0,
        kill_switch=False,
    )
    defaults.update(overrides)
    return RiskChecker(**defaults)


def test_kill_switch_blocks_all_trades():
    checker = make_checker(kill_switch=True)
    allowed, reason = checker.can_trade(size_usd=10, spread_pct=1.0,
                                         liquidity_usd=1000, open_positions=0,
                                         daily_loss=0)
    assert allowed is False
    assert "kill switch" in reason.lower()


def test_max_daily_loss_blocks_trade():
    checker = make_checker()
    # daily_loss = 11% of 1000 = $110, threshold is 10% = $100
    allowed, reason = checker.can_trade(size_usd=10, spread_pct=1.0,
                                         liquidity_usd=1000, open_positions=0,
                                         daily_loss=110)
    assert allowed is False
    assert "daily loss" in reason.lower()


def test_max_positions_blocks_trade():
    checker = make_checker(max_concurrent_positions=3)
    allowed, reason = checker.can_trade(size_usd=10, spread_pct=1.0,
                                         liquidity_usd=1000, open_positions=3,
                                         daily_loss=0)
    assert allowed is False
    assert "positions" in reason.lower()


def test_spread_too_wide_blocks_trade():
    checker = make_checker(max_spread_pct=5.0)
    allowed, reason = checker.can_trade(size_usd=10, spread_pct=6.0,
                                         liquidity_usd=1000, open_positions=0,
                                         daily_loss=0)
    assert allowed is False
    assert "spread" in reason.lower()


def test_size_exceeds_max_risk_blocks_trade():
    checker = make_checker()
    # max risk = 2% of 1000 = $20; trying to trade $25
    allowed, reason = checker.can_trade(size_usd=25, spread_pct=1.0,
                                         liquidity_usd=1000, open_positions=0,
                                         daily_loss=0)
    assert allowed is False
    assert "size" in reason.lower()


def test_low_liquidity_blocks_trade():
    checker = make_checker(min_liquidity_usd=500)
    allowed, reason = checker.can_trade(size_usd=10, spread_pct=1.0,
                                         liquidity_usd=200, open_positions=0,
                                         daily_loss=0)
    assert allowed is False
    assert "liquidity" in reason.lower()


def test_valid_trade_is_allowed():
    checker = make_checker()
    allowed, reason = checker.can_trade(size_usd=10, spread_pct=1.0,
                                         liquidity_usd=1000, open_positions=0,
                                         daily_loss=0)
    assert allowed is True

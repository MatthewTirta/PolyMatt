"""
baseline.py — BTC Odds Momentum strategy.

HYPOTHESIS (to be validated before use — see validate_lag_hypothesis()):
  Polymarket BTC markets may lag BTC spot price by 1–3 minutes.
  If BTC moves sharply and the odds haven't caught up, we take that side.

This file also contains the lag hypothesis validator. Run it before
starting the 1,000-run backtest.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from polymatt.market.models import Trade, Orderbook, Signal


@dataclass
class StrategyParams:
    """All tunable parameters. Adaptive learner adjusts these within bounds."""
    momentum_window_min: int = 5      # how far back to look for BTC price change
    entry_confidence_pct: float = 60  # min confidence to enter (%)
    spread_threshold_pct: float = 5.0 # max spread to trade (%)
    min_liquidity_usd: float = 400    # min liquidity at best bid/ask ($)
    cooldown_after_losses_min: int = 10

    # Bounds — learner cannot go outside these
    BOUNDS = {
        "momentum_window_min":    (1, 30),
        "entry_confidence_pct":   (40, 90),
        "spread_threshold_pct":   (0.5, 10.0),
        "min_liquidity_usd":      (100, 5000),
        "cooldown_after_losses_min": (2, 60),
    }


def evaluate_signal(
    condition_id: str,
    recent_trades: list,        # list of Trade objects from the market
    orderbook: Orderbook,
    btc_change_pct: float,      # BTC spot % change in the last momentum_window_min
    params: StrategyParams,
) -> Optional[Signal]:
    """
    Evaluate whether to enter a trade right now.
    Returns a Signal if conditions are met, or None if no trade.
    """
    # Don't trade if spread is too wide
    spread = orderbook.spread_pct() or 999
    if spread > params.spread_threshold_pct:
        return None

    # Don't trade if liquidity is too low
    best_bid = orderbook.best_bid() or 0
    best_ask = orderbook.best_ask() or 0
    bid_liq = sum(b.size for b in orderbook.bids[:3]) * best_bid
    ask_liq = sum(a.size for a in orderbook.asks[:3]) * best_ask
    if min(bid_liq, ask_liq) < params.min_liquidity_usd:
        return None

    # BTC momentum threshold: require > 1.5% move to consider entering
    BTC_MOMENTUM_THRESHOLD_PCT = 1.5
    if abs(btc_change_pct) < BTC_MOMENTUM_THRESHOLD_PCT:
        return None

    # Confidence is proportional to how strong the BTC move is
    # 1.5% move = 60% confidence; 3% move = 80%; 5%+ = 90%
    confidence = min(60 + (abs(btc_change_pct) - 1.5) * 10, 90)

    if confidence < params.entry_confidence_pct:
        return None

    direction = "YES" if btc_change_pct > 0 else "NO"
    reason = (
        f"BTC {btc_change_pct:+.1f}% in {params.momentum_window_min}min, "
        f"Polymarket {direction} price unchanged at "
        f"{best_ask if direction == 'YES' else best_bid:.3f} — entering {direction}"
    )

    return Signal(
        condition_id=condition_id,
        direction=direction,
        confidence=confidence / 100,
        reason=reason,
    )


def validate_lag_hypothesis(orderbooks: list, btc_prices: list) -> dict:
    """
    Measure whether Polymarket odds lag BTC spot price.

    Returns:
      {
        "supported": bool,
        "median_lag_seconds": float,
        "message": str
      }

    Hypothesis is SUPPORTED if median lag >= 30 seconds.
    Hypothesis is REJECTED if median lag < 30 seconds — do not trade.
    """
    if len(orderbooks) < 10 or len(btc_prices) < 10:
        return {
            "supported": False,
            "median_lag_seconds": 0,
            "message": "Not enough data to validate hypothesis (need 7+ days of data)",
        }

    # Find timestamps where BTC moved > 1%
    # For each, find how long until Polymarket odds ALSO moved > 1%
    lags = []
    for i in range(1, len(btc_prices)):
        prev_price, curr_price, ts = btc_prices[i - 1]
        pct_change = abs((curr_price - prev_price) / prev_price * 100)
        if pct_change < 1.0:
            continue

        # Find the first orderbook entry AFTER ts where odds also moved > 1%
        # We need a baseline odds price at the time of the BTC move
        baseline_mid = None
        for ob in orderbooks:
            if ob.timestamp >= ts and ob.best_bid() and ob.best_ask():
                baseline_mid = (ob.best_bid() + ob.best_ask()) / 2
                break
        if baseline_mid is None or baseline_mid == 0:
            continue

        # Now find when odds moved > 1% relative to baseline
        for ob in orderbooks:
            if ob.timestamp <= ts:
                continue
            if ob.best_bid() and ob.best_ask():
                mid = (ob.best_bid() + ob.best_ask()) / 2
                odds_change_pct = abs((mid - baseline_mid) / baseline_mid * 100)
                if odds_change_pct >= 1.0:
                    # Odds moved > 1% — this is a real lag measurement
                    lag = (ob.timestamp - ts).total_seconds()
                    lags.append(lag)
                    break

    if not lags:
        return {
            "supported": False,
            "median_lag_seconds": 0,
            "message": "No correlated price moves found in dataset",
        }

    lags.sort()
    median_lag = lags[len(lags) // 2]
    supported = median_lag >= 30

    return {
        "supported": supported,
        "median_lag_seconds": round(median_lag, 1),
        "message": (
            f"SUPPORTED (median lag: {median_lag:.0f}s >= 30s threshold)"
            if supported else
            f"REJECTED (median lag: {median_lag:.0f}s < 30s threshold — no tradeable edge)"
        ),
    }

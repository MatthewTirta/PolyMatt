"""
backtest/engine.py — Run N simulated trading sessions on stored historical data.

Before running 1,000 simulations, validates the BTC lag hypothesis.
If the hypothesis is rejected (no lag found), stops and reports "no edge".

Requires at least 7 days of stored data from Phase 1.
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Optional
from polymatt import config
from polymatt.data.storage import get_trades_since, get_orderbooks_since
from polymatt.market.discover import get_btc_markets
from polymatt.strategy.baseline import StrategyParams, evaluate_signal, validate_lag_hypothesis
from polymatt.strategy.learner import Learner
from polymatt.paper_trader.portfolio import Portfolio
from polymatt.paper_trader.risk import make_risk_checker_from_config

logger = logging.getLogger(__name__)

TAKER_FEE = 0.02   # 2% fee on each trade
SLIPPAGE = 0.005   # 0.5% assumed slippage


def run_backtest(
    num_runs: int = 1000,
    session_duration_min: int = 15,
    learn: bool = False,
) -> dict:
    """
    Run the backtest.

    1. Validates lag hypothesis (exits with message if rejected)
    2. Runs num_runs independent simulated sessions
    3. Returns aggregate statistics
    """
    print(f"[PolyMatt] Starting {num_runs}-run backtest ({session_duration_min}min each)...")

    # Load stored data
    from polymatt.data.storage import get_btc_prices_since
    markets = get_btc_markets()
    if not markets:
        return {"error": "No BTC markets found"}

    market = markets[0]
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    trades = get_trades_since(market.condition_id, seven_days_ago)
    orderbooks = get_orderbooks_since(market.condition_id, seven_days_ago)
    btc_raw = get_btc_prices_since(seven_days_ago)  # [(timestamp, price_usd)]

    if len(trades) < 100 or len(orderbooks) < 100:
        print("[PolyMatt] Not enough stored data. Run watch_orderbook for at least 7 days first.")
        return {"error": "insufficient data"}

    if len(btc_raw) < 50:
        print("[PolyMatt] Not enough BTC price data. watch_orderbook collects this automatically.")
        return {"error": "insufficient_btc_data"}

    # Build (prev_price, curr_price, timestamp) tuples for lag validator
    btc_price_tuples = [
        (btc_raw[i][1], btc_raw[i+1][1], btc_raw[i][0])
        for i in range(len(btc_raw)-1)
    ]

    # Validate lag hypothesis
    result = validate_lag_hypothesis(orderbooks, btc_price_tuples)
    print(f"  Lag hypothesis : {result['message']}")
    if not result["supported"]:
        return {"error": "hypothesis_rejected", "message": result["message"]}

    # Run simulations
    learner = Learner() if learn else None
    params = learner.get_params() if learner else StrategyParams()

    btc_prices = btc_raw  # [(timestamp, price_usd)] — real spot data

    results = []
    for run in range(num_runs):
        win_rate, pnl, drawdown = _simulate_session(
            trades, orderbooks, btc_prices, session_duration_min, params
        )
        results.append({"win_rate": win_rate, "pnl": pnl, "max_drawdown": drawdown})

        if learner and (run + 1) % 10 == 0:
            avg_wr = sum(r["win_rate"] for r in results[-10:]) / 10
            learner.record_session(avg_wr, params, [])
            params = learner.get_params()

        if (run + 1) % 100 == 0:
            print(f"  {run + 1}/{num_runs} runs complete...", flush=True)

    # Aggregate stats
    win_rates = [r["win_rate"] for r in results]
    pnls = [r["pnl"] for r in results]
    drawdowns = [r.get("max_drawdown", 0) for r in results]
    avg_wr = sum(win_rates) / len(win_rates)
    avg_pnl = sum(pnls) / len(pnls)
    success_rate = sum(1 for p in pnls if p > 0) / len(pnls)

    # Cross-run PnL consistency ratio (mean / stdev of per-session PnL).
    # NOTE: this is NOT a time-series Sharpe — it measures how consistently
    # the strategy produces positive PnL across runs, not risk-adjusted return.
    # A value > 0.5 is good; > 1.0 is strong. Not comparable to published Sharpe ratios.
    import statistics
    pnl_std = statistics.stdev(pnls) if len(pnls) > 1 else 0
    sharpe = round(avg_pnl / pnl_std, 2) if pnl_std > 0 else 0

    stats = {
        "runs": num_runs,
        "lag_median_seconds": result["median_lag_seconds"],
        "win_rate_avg_pct": round(avg_wr * 100, 1),
        "pnl_avg": round(avg_pnl, 2),
        "pnl_worst": round(min(pnls), 2),
        "pnl_best": round(max(pnls), 2),
        "max_drawdown_worst_pct": round(max(drawdowns) / config.PAPER_BANKROLL_USD * 100, 1),
        "sharpe_ratio": sharpe,
        "success_rate_pct": round(success_rate * 100, 1),
        "verdict": _verdict(avg_wr, success_rate),
    }
    return stats


def _simulate_session(trades, orderbooks, btc_prices, duration_min, params):
    """
    Simulate one paper trading session on stored historical data.

    Uses real BTC spot prices to estimate BTC momentum (not a proxy).
    Returns (win_rate 0-1, total_pnl, max_drawdown).
    """
    # Random start point — prevents curve-fitting to one lucky window
    max_start = max(0, len(orderbooks) - duration_min * 2)
    start_idx = random.randint(0, max_start)
    end_idx = min(start_idx + duration_min * 2, len(orderbooks))
    session_obs = orderbooks[start_idx:end_idx]
    if not session_obs:
        return 0.0, 0.0, 0.0

    session_start = session_obs[0].timestamp
    session_end = session_obs[-1].timestamp
    session_trades = [t for t in trades if session_start <= t.timestamp <= session_end]

    # Get BTC prices covering this session window
    session_btc = [(ts, p) for ts, p in btc_prices
                   if session_start <= ts <= session_end]

    portfolio = Portfolio(config.PAPER_BANKROLL_USD)
    risk = make_risk_checker_from_config(config.PAPER_BANKROLL_USD)

    for i, ob in enumerate(session_obs[1:], 1):
        # Calculate BTC % change over the momentum window using real spot prices
        window_seconds = params.momentum_window_min * 60
        cutoff = ob.timestamp - timedelta(seconds=window_seconds)
        window_btc = [(ts, p) for ts, p in session_btc if cutoff <= ts <= ob.timestamp]

        if len(window_btc) < 2:
            continue
        btc_change_pct = ((window_btc[-1][1] - window_btc[0][1]) / window_btc[0][1]) * 100

        signal = evaluate_signal(ob.condition_id, session_trades, ob,
                                  btc_change_pct=btc_change_pct, params=params)
        if signal is None:
            continue

        liq = sum(b.size for b in ob.bids[:3]) * (ob.best_bid() or 0)
        allowed, _ = risk.can_trade(
            size_usd=20.0, spread_pct=ob.spread_pct() or 0,
            liquidity_usd=liq, open_positions=0,
            daily_loss=portfolio.daily_loss,
        )
        if not allowed:
            continue

        # Simulate trade result with fees and slippage
        entry = ob.best_ask() or 0.5
        exit_price = entry + (0.02 * (1 if signal.direction == "YES" else -1))
        gross_pnl = (exit_price - entry) * 20
        net_pnl = gross_pnl - (20 * TAKER_FEE) - (20 * SLIPPAGE)
        portfolio.record_closed_trade(net_pnl)

    return portfolio.win_rate() / 100, portfolio.total_pnl, portfolio.max_drawdown


def _verdict(win_rate, success_rate):
    if win_rate < 0.52:
        return "DO NOT TRADE — no edge found after fees"
    if win_rate < 0.58 or success_rate < 0.60:
        return "PAPER TRADE ONLY — marginal edge"
    return "MANUAL ORDER-TICKET — edge confirmed, consider live trading manually"

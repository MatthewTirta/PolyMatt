"""
paper_trade.py — CLI: run the paper trader for a set duration.

Usage:
  python -m polymatt.scripts.paper_trade --duration 15m
  python -m polymatt.scripts.paper_trade --duration 30m
  python -m polymatt.scripts.paper_trade          # runs until Ctrl+C
"""
import asyncio
import argparse
import json
import logging
import os
from datetime import datetime
from polymatt.config import check_kill_switch
from polymatt.data.storage import init_db
from polymatt.data.preflight import run_preflight
from polymatt.data.feed import stream_market
from polymatt.market.discover import get_btc_markets
from polymatt.paper_trader.trader import PaperTrader
from polymatt.strategy.learner import Learner
from polymatt.notifications import send as notify
from polymatt.charts import save_session_pnl_chart, save_winrate_trend_chart, save_parameter_evolution_chart

logger = logging.getLogger(__name__)
SESSION_LOG = "logs/sessions.json"


def load_session_history():
    try:
        with open(SESSION_LOG) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_session_history(history):
    os.makedirs("logs", exist_ok=True)
    with open(SESSION_LOG, "w") as f:
        json.dump(history, f, indent=2)


def parse_duration(s):
    if s is None:
        return None
    return int(s.replace("m", "").replace("min", ""))


def main():
    check_kill_switch()
    init_db()

    parser = argparse.ArgumentParser(description="Run PolyMatt paper trader")
    parser.add_argument("--duration", default=None, help="e.g. 15m, 30m")
    args = parser.parse_args()

    run_preflight()

    markets = get_btc_markets()
    if not markets:
        print("[PolyMatt] No BTC markets found.")
        return

    market = markets[0]
    duration_min = parse_duration(args.duration)
    history = load_session_history()
    session_num = len(history) + 1

    learner = Learner()
    trader = PaperTrader(condition_id=market.condition_id, learner=learner)
    stop_event = asyncio.Event()

    print(f"[PolyMatt] Starting paper trader — Session #{session_num}")
    print(f"  Market   : {market.question[:60]}")
    print(f"  Duration : {args.duration or 'unlimited (Ctrl+C to stop)'}\n")

    async def run():
        feed_task = asyncio.create_task(
            stream_market(market.condition_id,
                          on_orderbook=trader.on_orderbook,
                          stop_event=stop_event,
                          notify_fn=notify)
        )
        trade_task = asyncio.create_task(trader.run_loop(stop_event))

        if duration_min:
            await asyncio.sleep(duration_min * 60)
            stop_event.set()

        try:
            await asyncio.gather(feed_task, trade_task)
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        stop_event.set()

    summary = trader.close_session()
    history.append({"session": session_num, "timestamp": datetime.utcnow().isoformat(),
                    **summary})
    save_session_history(history)

    win_rates = [s["win_rate_pct"] for s in history]
    chart_path = save_session_pnl_chart(session_num, [0])
    save_winrate_trend_chart(win_rates)
    save_parameter_evolution_chart(learner.param_versions)

    print(f"\n[PolyMatt] Session #{session_num} complete")
    print(f"  Trades made           : {summary['wins'] + summary['losses']}")
    print(f"  Win rate              : {summary['win_rate_pct']}%")
    print(f"  Net PnL               : ${summary['total_pnl']:+.2f}")
    print(f"  Max drawdown          : -${summary['max_drawdown']:.2f}")
    print(f"  All-time win rate     : {sum(win_rates)/len(win_rates):.1f}%")
    if chart_path:
        print(f"  Chart saved           : {chart_path}")

    notify(
        f"[PolyMatt] Session #{session_num} complete\n"
        f"Win rate: {summary['win_rate_pct']}%  PnL: ${summary['total_pnl']:+.2f}"
    )


if __name__ == "__main__":
    main()

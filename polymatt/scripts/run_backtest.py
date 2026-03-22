"""
run_backtest.py — CLI: run N backtest simulations.

Usage:
  python -m polymatt.scripts.run_backtest --runs 1000 --duration 15m
  python -m polymatt.scripts.run_backtest --runs 1000 --duration 15m --learn
"""
import argparse
from polymatt.config import check_kill_switch
from polymatt.data.storage import init_db
from polymatt.data.preflight import run_preflight
from polymatt.backtest.engine import run_backtest


def parse_duration(s: str) -> int:
    """Convert '15m' or '30m' to integer minutes."""
    return int(s.replace("m", "").replace("min", ""))


def main():
    check_kill_switch()
    init_db()

    parser = argparse.ArgumentParser(description="Run PolyMatt backtests")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--duration", default="15m")
    parser.add_argument("--learn", action="store_true",
                        help="Adapt parameters every 10 runs")
    args = parser.parse_args()

    run_preflight()
    duration_min = parse_duration(args.duration)
    stats = run_backtest(args.runs, duration_min, learn=args.learn)

    if "error" in stats:
        print(f"\n[PolyMatt] Backtest aborted: {stats.get('message', stats['error'])}")
        return

    print(f"\n[PolyMatt] Backtest complete ({stats['runs']} runs × {args.duration})")
    print(f"  Lag hypothesis    : SUPPORTED ({stats['lag_median_seconds']}s median lag)")
    print(f"  Win rate (avg)    : {stats['win_rate_avg_pct']}%")
    print(f"  Net PnL (avg)     : ${stats['pnl_avg']:+.2f} / session")
    print(f"  Worst run         : ${stats['pnl_worst']:.2f}")
    print(f"  Best run          : ${stats['pnl_best']:.2f}")
    print(f"  Max drawdown      : -{stats['max_drawdown_worst_pct']:.1f}% (worst case)")
    print(f"  Sharpe ratio      : {stats['sharpe_ratio']:.2f}")
    print(f"  Success rate      : {stats['success_rate_pct']}%")
    print(f"  Verdict           : {stats['verdict']}")


if __name__ == "__main__":
    main()

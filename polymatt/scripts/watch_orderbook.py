"""
watch_orderbook.py — CLI: stream a live orderbook to the terminal.

Usage:
  python -m polymatt.scripts.watch_orderbook --id CONDITION_ID
"""
import asyncio
import argparse
from polymatt.config import check_kill_switch
from polymatt.data.storage import init_db
from polymatt.data.feed import stream_market
from polymatt.data.btc_price import start_collection as start_btc_collection
from polymatt.market.models import Orderbook, Trade


def on_orderbook(ob: Orderbook):
    bid = ob.best_bid() or 0
    ask = ob.best_ask() or 0
    spread = ob.spread_pct() or 0
    print(f"  [{ob.timestamp.strftime('%H:%M:%S')}]  "
          f"BID {bid:.3f}  ASK {ask:.3f}  SPREAD {spread:.2f}%")


def on_trade(trade: Trade):
    print(f"  [{trade.timestamp.strftime('%H:%M:%S')}]  "
          f"TRADE {trade.side} @ {trade.price:.3f}  size={trade.size:.2f}")


def main():
    check_kill_switch()
    init_db()

    parser = argparse.ArgumentParser(description="Stream live orderbook for a BTC market")
    parser.add_argument("--id", required=True, help="Market condition_id to watch")
    args = parser.parse_args()

    print(f"[PolyMatt] Streaming market {args.id} — press Ctrl+C to stop\n")
    stop = asyncio.Event()

    async def run():
        feed_task = asyncio.create_task(stream_market(
            condition_id=args.id,
            on_trade=on_trade,
            on_orderbook=on_orderbook,
            stop_event=stop,
        ))
        btc_task = asyncio.create_task(start_btc_collection(stop))
        await asyncio.gather(feed_task, btc_task)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        stop.set()
        print("\n[PolyMatt] Stopped.")


if __name__ == "__main__":
    main()

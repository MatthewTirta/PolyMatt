"""
fetch_markets.py — CLI: list all BTC markets or inspect one.

Usage:
  python -m polymatt.scripts.fetch_markets
  python -m polymatt.scripts.fetch_markets --id CONDITION_ID
"""
import argparse
from polymatt.config import check_kill_switch
from polymatt.data.storage import init_db
from polymatt.market.discover import get_btc_markets
from polymatt.market.client import get_client, fetch_orderbook


def main():
    check_kill_switch()
    init_db()

    parser = argparse.ArgumentParser(description="List or inspect BTC markets on Polymarket")
    parser.add_argument("--id", help="Inspect a single market by condition_id")
    args = parser.parse_args()

    markets = get_btc_markets()

    if not markets:
        print("[PolyMatt] No BTC markets found.")
        return

    if args.id:
        # Show detailed view of one market
        market = next((m for m in markets if m.condition_id == args.id), None)
        if not market:
            print(f"[PolyMatt] Market {args.id} not found.")
            return
        client = get_client()
        ob = fetch_orderbook(client, market.condition_id)
        bids = ob.get("bids", [])[:5]
        asks = ob.get("asks", [])[:5]
        print(f"\n{market.question}")
        print(f"  ID       : {market.condition_id}")
        print(f"  YES price: {market.yes_price:.3f}  NO price: {market.no_price:.3f}")
        print(f"  Volume   : ${market.volume_usd:,.0f}")
        print(f"  Ends     : {market.end_date}")
        print(f"\n  Top 5 bids: {[b['price'] for b in bids]}")
        print(f"  Top 5 asks: {[a['price'] for a in asks]}")
    else:
        # List all BTC markets
        print(f"\n[PolyMatt] Found {len(markets)} BTC markets:\n")
        for m in markets:
            print(f"  [{m.condition_id[:8]}...]  YES={m.yes_price:.2f}  "
                  f"Vol=${m.volume_usd:,.0f}  {m.question[:60]}")


if __name__ == "__main__":
    main()

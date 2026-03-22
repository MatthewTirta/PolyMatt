"""
preflight.py — Check data quality before starting any session.

Scores 0–100 using three checks:
  40 pts: API reachable + BTC markets found
  30 pts: best market spread is within threshold
  30 pts: at least 50 trades recorded in the last hour

If score < 80, the program exits with a clear explanation.
"""
import sys
import logging
from polymatt import config
from polymatt.market.client import get_client, fetch_orderbook
from polymatt.market.discover import get_btc_markets
from polymatt.data.storage import get_trade_count_last_hour

logger = logging.getLogger(__name__)
TRADE_THRESHOLD = 50


def run_preflight() -> int:
    """Run all checks and return the score. Exits if score < 80."""
    print("[PolyMatt] Running pre-flight data check...")
    score = 0
    markets = []

    # Check 1: API reachable + BTC markets found (40 pts)
    try:
        markets = get_btc_markets()
        if markets:
            print(f"  ✓ API reachable                    (40/40)")
            print(f"  ✓ BTC markets found: {len(markets)}")
            score += 40
        else:
            print("  ✗ No BTC markets found             (0/40)")
    except Exception as e:
        print(f"  ✗ API unreachable: {e}  (0/40)")

    # Check 2: spread within threshold (30 pts)
    if markets:
        try:
            client = get_client()
            ob_raw = fetch_orderbook(client, markets[0].condition_id)
            bids = ob_raw.get("bids", [])
            asks = ob_raw.get("asks", [])
            if bids and asks:
                best_bid = max(float(b["price"]) for b in bids)
                best_ask = min(float(a["price"]) for a in asks)
                mid = (best_bid + best_ask) / 2
                spread = ((best_ask - best_bid) / mid) * 100 if mid > 0 else 999
                if spread <= config.MAX_SPREAD_PCT:
                    print(f"  ✓ Orderbook spread: {spread:.1f}%         (30/30)")
                    score += 30
                else:
                    print(f"  ✗ Spread too wide: {spread:.1f}% > {config.MAX_SPREAD_PCT}%  (0/30)")
            else:
                print("  ✗ Empty orderbook              (0/30)")
        except Exception as e:
            print(f"  ✗ Spread check failed: {e}      (0/30)")

    # Check 3: trade history in last hour (30 pts)
    if markets:
        try:
            count = get_trade_count_last_hour(markets[0].condition_id)
            if count >= TRADE_THRESHOLD:
                print(f"  ✓ Trade history: {count}/1h             (30/30)")
                score += 30
            else:
                print(f"  ✗ Low trade history: {count}/1h < {TRADE_THRESHOLD}  (0/30)")
        except Exception as e:
            print(f"  ✗ Trade history check failed: {e}  (0/30)")

    status = "READY" if score >= 80 else "NOT READY"
    print(f"\n  Data quality score: {score}% — {status}")

    if score < 80:
        print("\n[PolyMatt] Data quality too low. Fix the issues above and try again.")
        sys.exit(1)

    return score

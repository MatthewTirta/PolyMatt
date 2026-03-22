"""
auto_trade.py — Fully automated paper-trading bot for Bitcoin Up or Down (5-minute markets).

Every cycle the bot:
  1. Finds the current or next "Bitcoin Up or Down" 5-minute market on Polymarket
  2. Samples BTC price from CoinGecko to measure the 5-minute trend
  3. Picks Up (if BTC trending up) or Down (if BTC trending down)
  4. Records a simulated bet — NO real money is spent
  5. Waits for the 5-minute window to close and the oracle to resolve
  6. Calculates your profit or loss at true Polymarket odds
  7. Loops until the session duration is reached

Usage:
  python -m polymatt.scripts.auto_trade --duration 40m
  python -m polymatt.scripts.auto_trade --duration 40m --size 5
"""
import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
GAMMA_API = "https://gamma-api.polymarket.com/markets"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
TAKER_FEE_PCT = 0.01   # 1% of wagered amount (conservative estimate)
LOG_FILE = "logs/auto_trade_sessions.json"


# ── API helpers ───────────────────────────────────────────────────────────────

def _get(url, params=None, timeout=10):
    """GET request. Returns parsed JSON or None on error."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("GET %s failed: %s", url, e)
        return None


def _parse_prices(market: dict) -> dict:
    """
    Return {outcome_name: price} from a Gamma API market dict.
    e.g. {"Up": 0.52, "Down": 0.48}
    """
    outcomes = market.get("outcomes", [])
    raw = market.get("outcomePrices", [])
    # The Gamma API sometimes returns this as a JSON string instead of a list
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            raw = []
    result = {}
    for i, outcome in enumerate(outcomes):
        try:
            result[outcome] = float(raw[i]) if i < len(raw) else 0.50
        except (ValueError, TypeError):
            result[outcome] = 0.50
    return result


def _parse_dt(s: str | None):
    """Parse an ISO 8601 datetime string into a timezone-aware datetime. Returns None on failure."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Market discovery ──────────────────────────────────────────────────────────

def _is_5min_market(question: str) -> bool:
    """
    True if the question looks like a 5-minute window market.
    5-min format: "Bitcoin Up or Down - March 23, 8:20AM-8:25AM ET"
    Daily format: "Bitcoin Up or Down on March 22?"  ← exclude
    """
    q = question.lower()
    if "bitcoin up or down" not in q:
        return False
    # Must have a time range like "8:20am-8:25am" (two times with a dash)
    # Daily markets say "on March 22?" and have no time
    return ("am-" in q or "pm-" in q or "am –" in q or "pm –" in q
            or ("am" in q and "et" in q and "-" in q))


def find_next_market() -> tuple:
    """
    Find the best Bitcoin Up or Down 5-minute market to trade right now.

    Returns (market_dict, wait_seconds) where:
    - wait_seconds == 0 means the 5-min window is currently open → bet immediately
    - wait_seconds >  0 means the window hasn't opened yet → wait before betting
    - market_dict == None means nothing suitable found
    """
    now = datetime.now(timezone.utc)

    data = _get(GAMMA_API, params={
        "active": "true",
        "closed": "false",
        "order": "startDate",
        "ascending": "false",
        "limit": 50,
    })
    if not data:
        return None, 0

    candidates = []
    for m in data:
        if not _is_5min_market(m.get("question", "")):
            continue
        # We need both an event start time and an end date to know the window
        if m.get("eventStartTime") or m.get("startDate"):
            if m.get("endDate"):
                candidates.append(m)

    if not candidates:
        return None, 0

    # Sort by eventStartTime ascending so the nearest window comes first
    candidates.sort(key=lambda m: _parse_dt(m.get("eventStartTime") or m.get("startDate")) or now)

    for m in candidates:
        start_dt = _parse_dt(m.get("eventStartTime") or m.get("startDate"))
        end_dt   = _parse_dt(m.get("endDate"))
        if start_dt is None or end_dt is None:
            continue
        if start_dt <= now <= end_dt:
            # Window is open right now
            return m, 0
        if start_dt > now:
            # Future window — return the nearest one
            wait = (start_dt - now).total_seconds()
            return m, max(0.0, wait)

    return None, 0


def poll_resolution(condition_id: str, max_wait_seconds: int = 300) -> str | None:
    """
    Poll Gamma API until the market closes and a winner is known.
    Returns the winning outcome name (e.g. "Up" or "Down"), or None if timed out.
    """
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        data = _get(GAMMA_API, params={"conditionId": condition_id})
        if data:
            m = data[0] if isinstance(data, list) else None
            if m and m.get("closed"):
                prices = _parse_prices(m)
                for outcome, price in prices.items():
                    if price >= 0.95:   # near 1.0 = resolved winner
                        return outcome
        time.sleep(30)
    return None


# ── Trading bot ───────────────────────────────────────────────────────────────

class AutoTrader:
    """
    Paper-trading loop for Bitcoin Up or Down 5-minute markets.
    Simulates $`size_usd` bets using BTC momentum as the signal.
    No real money is ever spent.
    """

    def __init__(self, duration_min: int, size_usd: float):
        self.duration_min = duration_min
        self.size_usd = size_usd
        self.bets: list = []
        self._btc_samples: list = []   # list of (unix_timestamp, price)

    # ── Price helpers ─────────────────────────────────────────────────────────

    def _sample_btc(self) -> float:
        """Fetch current BTC/USD from CoinGecko and store the sample."""
        try:
            resp = requests.get(COINGECKO_URL, timeout=10)
            price = float(resp.json()["bitcoin"]["usd"])
        except Exception:
            price = 0.0
        if price > 0:
            self._btc_samples.append((time.time(), price))
            self._btc_samples = self._btc_samples[-40:]  # keep ~40 min of data
        return price

    def _trend_5m(self) -> float:
        """
        % change in BTC price over the last 5 minutes.
        Positive = BTC went up, negative = BTC went down.
        Returns 0.0 if not enough data yet.
        """
        if len(self._btc_samples) < 2:
            return 0.0
        now = time.time()
        target_ts = now - 300   # 5 minutes ago
        # Find the sample whose timestamp is closest to 5 minutes ago
        old = min(self._btc_samples, key=lambda s: abs(s[0] - target_ts))
        cur = self._btc_samples[-1][1]
        return (cur - old[1]) / old[1] * 100 if old[1] > 0 else 0.0

    # ── Signal ────────────────────────────────────────────────────────────────

    def _decide(self, trend_pct: float) -> str:
        """
        Momentum strategy: follow the 5-minute BTC trend.
          BTC trending up   → bet Up
          BTC trending down → bet Down
          Flat (0%)         → bet Up (slight long bias)
        """
        return "Up" if trend_pct >= 0 else "Down"

    # ── P&L ───────────────────────────────────────────────────────────────────

    def _calc_pnl(self, direction: str, entry_price: float, outcome: str) -> float:
        """
        Calculate net P&L for one settled bet.

        How Polymarket odds work:
          - You spend $size to buy (size / entry_price) shares
          - If your side wins, each share pays $1.00
          - If your side loses, shares pay $0.00
          - Fee = size * TAKER_FEE_PCT

        Example: bet $1 on Up @ 0.52
          Shares bought = 1 / 0.52 = 1.923
          Win  → receive $1.923, gross profit = $0.923
          Lose → receive $0.000, gross loss   = −$1.000
        """
        won = (outcome == direction)
        if won:
            gross = self.size_usd * (1.0 / entry_price - 1.0)
        else:
            gross = -self.size_usd
        fee = self.size_usd * TAKER_FEE_PCT
        return round(gross - fee, 4)

    # ── Display ───────────────────────────────────────────────────────────────

    def _print_running(self):
        """Print a one-line running win/loss/PnL summary."""
        settled = [b for b in self.bets if b["pnl"] is not None]
        if not settled:
            return
        wins = sum(1 for b in settled if b["pnl"] > 0)
        total_pnl = sum(b["pnl"] for b in settled)
        wr = wins / len(settled) * 100
        print(f"  Running  │  {wins}W / {len(settled)-wins}L  "
              f"Win rate: {wr:.0f}%  Total PnL: ${total_pnl:+.4f}")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        approx_cycles = self.duration_min // 5
        print(f"\n{'═'*62}")
        print(f"  PolyMatt  ·  Auto Paper Trader")
        print(f"  Market    : Bitcoin Up or Down (5-minute windows)")
        print(f"  Duration  : {self.duration_min} min  ·  ~{approx_cycles} bets  ·  ${self.size_usd:.2f}/bet")
        print(f"  Strategy  : BTC 5-min momentum → Up or Down")
        print(f"  Mode      : PAPER TRADE  (no real money)")
        print(f"{'═'*62}\n")

        session_end = time.time() + self.duration_min * 60
        seen_markets: set = set()
        cycle = 0

        # Collect an initial BTC price sample so the first trend is meaningful
        btc_now = self._sample_btc()
        print(f"  BTC now   : ${btc_now:,.2f}  (sampling for 5-min trend baseline...)\n")

        while time.time() < session_end:

            # ── Find market ──────────────────────────────────────────
            market, wait_secs = find_next_market()

            if market is None:
                print("  ⚠  No active market found — retrying in 60s...")
                time.sleep(min(60, session_end - time.time()))
                continue

            condition_id = market.get("conditionId", "")
            question     = market.get("question", "?")

            # Already traded this window — wait a bit for the next one
            if condition_id in seen_markets:
                sleep_secs = min(30, session_end - time.time())
                if sleep_secs <= 0:
                    break
                time.sleep(sleep_secs)
                continue

            # ── Wait for window to open ───────────────────────────────
            if wait_secs > 0:
                remaining = session_end - time.time()
                if wait_secs > remaining:
                    print(f"  ⏸  Next window opens in {int(wait_secs)}s — "
                          f"past session end. Stopping.")
                    break
                m, s = int(wait_secs // 60), int(wait_secs % 60)
                print(f"  ⏳ Waiting {m}m {s}s for window: {question}")
                waited = 0
                while waited < wait_secs and time.time() < session_end:
                    sleep_chunk = min(60, wait_secs - waited)
                    time.sleep(sleep_chunk)
                    waited += sleep_chunk
                    self._sample_btc()   # keep trend data fresh during the wait
                # Refresh market data after waiting (prices may have changed)
                fresh = _get(GAMMA_API, params={"conditionId": condition_id})
                if fresh and isinstance(fresh, list) and fresh:
                    market = fresh[0]

            seen_markets.add(condition_id)
            cycle += 1

            # ── Decide direction ──────────────────────────────────────
            btc_price = self._sample_btc()
            trend_pct = self._trend_5m()
            direction = self._decide(trend_pct)
            prices    = _parse_prices(market)
            entry     = prices.get(direction, 0.50)
            # If entry is 0 or 1, the market isn't priced yet — use 0.50
            if entry < 0.01 or entry > 0.99:
                entry = 0.50

            print(f"{'─'*62}")
            print(f"  Cycle {cycle}  │  {datetime.now().strftime('%H:%M:%S')}")
            print(f"  Market   │  {question}")
            print(f"  BTC      │  ${btc_price:,.2f}  ({trend_pct:+.2f}% over last 5m)")
            arrow = "↑ UP  " if direction == "Up" else "↓ DOWN"
            print(f"  Signal   │  {arrow}  (entry price: {entry:.3f})")
            print(f"  Bet      │  ${self.size_usd:.2f} on {direction.upper()}")

            # Record the simulated bet
            bet = {
                "cycle":         cycle,
                "condition_id":  condition_id,
                "question":      question,
                "direction":     direction,
                "entry_price":   entry,
                "size_usd":      self.size_usd,
                "btc_price":     btc_price,
                "btc_trend_pct": round(trend_pct, 3),
                "entry_time":    datetime.now(timezone.utc).isoformat(),
                "outcome":       None,
                "pnl":           None,
            }
            self.bets.append(bet)

            # ── Wait for the window to close ──────────────────────────
            end_dt = _parse_dt(market.get("endDate"))
            now_dt = datetime.now(timezone.utc)

            if end_dt and end_dt > now_dt:
                window_remaining = (end_dt - now_dt).total_seconds()
                # +90 seconds buffer for Chainlink oracle to report
                resolve_wait = min(window_remaining + 90, session_end - time.time())
            else:
                resolve_wait = min(300, session_end - time.time())

            print(f"  Waiting  │  {int(resolve_wait)}s for market to resolve...")

            waited = 0
            while waited < resolve_wait and time.time() < session_end:
                sleep_chunk = min(60, resolve_wait - waited)
                time.sleep(sleep_chunk)
                waited += sleep_chunk
                self._sample_btc()

            # ── Check resolution ──────────────────────────────────────
            print(f"  Checking │  polling Gamma API for outcome...")
            outcome = poll_resolution(condition_id, max_wait_seconds=180)

            if outcome:
                net_pnl = self._calc_pnl(direction, entry, outcome)
                bet["outcome"] = outcome
                bet["pnl"]     = net_pnl
                icon = "✓  WON " if outcome == direction else "✗  LOST"
                print(f"  Result   │  {icon}  (resolved: {outcome})  "
                      f"PnL: ${net_pnl:+.4f}")
            else:
                bet["outcome"] = "pending"
                print(f"  Result   │  ⏳ Pending — oracle hasn't reported yet")

            self._print_running()
            print()

        # ── End of session ────────────────────────────────────────────
        self._print_summary()
        self._save_log()

    # ── Summary + logging ─────────────────────────────────────────────────────

    def _print_summary(self):
        settled = [b for b in self.bets if b["pnl"] is not None]
        pending = [b for b in self.bets if b["pnl"] is None]
        wins        = sum(1 for b in settled if b["pnl"] > 0)
        total_pnl   = sum(b["pnl"] for b in settled) if settled else 0.0
        total_waged = sum(b["size_usd"] for b in self.bets)
        wr  = wins / len(settled) * 100 if settled else 0
        roi = total_pnl / total_waged * 100 if total_waged > 0 else 0

        print(f"\n{'═'*62}")
        print(f"  SESSION COMPLETE  ·  Paper Trade (no real money)")
        print(f"{'═'*62}")
        print(f"  Bets placed     : {len(self.bets)}")
        print(f"  Settled / Pend. : {len(settled)} / {len(pending)}")
        print(f"  Wins / Losses   : {wins}W / {len(settled)-wins}L")
        print(f"  Win rate        : {wr:.0f}%")
        print(f"  Total wagered   : ${total_waged:.2f}")
        print(f"  Net PnL         : ${total_pnl:+.4f}")
        print(f"  ROI             : {roi:+.1f}%")
        print(f"{'═'*62}")
        print(f"  ⚠  This was PAPER TRADING — zero real money was used.")
        if pending:
            print(f"     {len(pending)} bet(s) pending — check {LOG_FILE} later.")
        print(f"     Full log saved to: {LOG_FILE}")
        print(f"{'═'*62}\n")

    def _save_log(self):
        """Append session results to logs/auto_trade_sessions.json."""
        os.makedirs("logs", exist_ok=True)
        existing = []
        try:
            with open(LOG_FILE) as f:
                existing = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        existing.append({
            "started":      datetime.now(timezone.utc).isoformat(),
            "duration_min": self.duration_min,
            "size_usd":     self.size_usd,
            "bets":         self.bets,
        })
        with open(LOG_FILE, "w") as f:
            json.dump(existing, f, indent=2)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="Auto paper-trade Bitcoin Up or Down every 5 minutes"
    )
    parser.add_argument(
        "--duration", default="40m",
        help="Total session length, e.g. 40m, 60m, 120m  (default: 40m)"
    )
    parser.add_argument(
        "--size", type=float, default=1.0,
        help="Simulated bet size in USD per cycle  (default: $1)"
    )
    args = parser.parse_args()

    duration_min = int(args.duration.replace("m", "").replace("min", ""))
    if duration_min < 5:
        print("Minimum duration is 5 minutes (one full cycle).")
        return

    AutoTrader(duration_min=duration_min, size_usd=args.size).run()


if __name__ == "__main__":
    main()

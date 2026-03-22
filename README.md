# PolyMatt

BTC-only Polymarket research stack and paper-trading bot.

**Hard boundaries:**
- No unattended real-money trading
- No automatic live order placement
- No geoblocking bypass or compliance evasion
- No martingale or hidden leverage
- No hardcoded secrets

## Requirements

- Python 3.11+

## Install & Run

```bash
# 1. Clone and set up
git clone https://github.com/YOUR_USERNAME/PolyMatt.git
cd PolyMatt
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_TOKEN, GITHUB_REPO

# 3. Run Phase 1 — discover BTC markets and stream live data
python -m polymatt.scripts.fetch_markets
python -m polymatt.scripts.watch_orderbook --id MARKET_ID

# 4. Run 1,000 backtest simulations with learning (requires >=7 days of stored data)
python -m polymatt.scripts.run_backtest --runs 1000 --duration 15m --learn

# 5. Run paper trader for 15 minutes
python -m polymatt.scripts.paper_trade --duration 15m

# 6. Run tests
pytest tests/

# 7. Reschedule a GitHub issue and cascade to all downstream issues
python scripts/reschedule.py --issue 3 --new-start 2026-04-25
```

## Project Structure

```
polymatt/           — main Python package
  config.py         — loads .env, validates all settings on startup
  market/           — Polymarket API client and market discovery
  data/             — WebSocket feed, SQLite storage, BTC price collection
  strategy/         — BTC Odds Momentum strategy + adaptive learner
  backtest/         — 1,000-run backtest harness
  paper_trader/     — risk controls, portfolio, paper trade execution
  notifications.py  — Telegram alerts (silently skipped if unconfigured)
  charts.py         — matplotlib session charts
  scripts/          — CLI entry points

scripts/            — utility scripts (GitHub issue management)
tests/              — pytest test suite
data/               — SQLite database (gitignored)
logs/               — log files (gitignored)
```

## Research

See [RESEARCH.md](RESEARCH.md) for the full Polymarket research document.

## Final Recommendation

To be determined after Issue #7 (capital analysis). Will be one of:
- **Do not trade** — lag hypothesis rejected, no edge found
- **Paper trade only** — marginal edge, not confident enough for real money
- **Manual order-ticket only** — edge confirmed (win rate >55%, Sharpe >1.0)

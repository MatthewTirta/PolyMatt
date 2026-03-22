"""
create_issues.py — One-time script to create all 7 PolyMatt GitHub issues.

Run once after creating the repo:
  python scripts/create_issues.py

Requires GITHUB_TOKEN and GITHUB_REPO in .env
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPO")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

ISSUES = [
    {
        "title": "Issue #1: Research + repo scaffold",
        "body": (
            "## Goal\nResearch Polymarket end-to-end and scaffold the PolyMatt repo.\n\n"
            "## Acceptance criteria\n"
            "- [ ] RESEARCH.md has all 12 sections with cited sources\n"
            "- [ ] Repo created with all files from spec Section 4\n"
            "- [ ] Tests pass: `pytest tests/`\n\n"
            "## Dates\nStart: 2026-03-22\nDue: 2026-04-05\n\n"
            "## Dependencies\nblocks: #2"
        ),
    },
    {
        "title": "Issue #2: Phase 1 — BTC market discovery",
        "body": (
            "## Goal\nBuild client.py, discover.py, models.py. CLI: fetch_markets.py.\n\n"
            "## Acceptance criteria\n"
            "- [ ] `python -m polymatt.scripts.fetch_markets` lists BTC markets\n"
            "- [ ] test_market.py passes\n\n"
            "## Dates\nStart: 2026-04-06\nDue: 2026-04-19\n\n"
            "## Dependencies\nblocked-by: #1\nblocks: #3"
        ),
    },
    {
        "title": "Issue #3: Phase 1 — Live orderbook/trade feed",
        "body": (
            "## Goal\nBuild feed.py with WebSocket reconnection. CLI: watch_orderbook.py.\n\n"
            "## Acceptance criteria\n"
            "- [ ] `python -m polymatt.scripts.watch_orderbook --id X` streams live data\n"
            "- [ ] Reconnects automatically on disconnect (5 retries)\n\n"
            "## Dates\nStart: 2026-04-20\nDue: 2026-05-03\n\n"
            "## Dependencies\nblocked-by: #2\nblocks: #4"
        ),
    },
    {
        "title": "Issue #4: Phase 1 — Local storage + CLI inspect",
        "body": (
            "## Goal\nBuild storage.py (SQLite). Pre-flight check. Start collecting live data.\n\n"
            "## Acceptance criteria\n"
            "- [ ] `watch_orderbook` saves to data/polymatt.db\n"
            "- [ ] Pre-flight check scores correctly\n"
            "- [ ] Data collection running for 7+ days before Issue #5 starts\n\n"
            "## Dates\nStart: 2026-05-04\nDue: 2026-05-17\n\n"
            "## Dependencies\nblocked-by: #3\nblocks: #5"
        ),
    },
    {
        "title": "Issue #5: Phase 2 — Baseline strategy + backtest",
        "body": (
            "## Goal\nValidate lag hypothesis. Build baseline.py and backtest engine. 1,000 runs.\n\n"
            "## Acceptance criteria\n"
            "- [ ] Lag hypothesis validation runs before backtest\n"
            "- [ ] `run_backtest --runs 1000 --learn` completes with verdict\n"
            "- [ ] test_strategy.py passes\n\n"
            "## Dates\nStart: 2026-05-18\nDue: 2026-05-31\n\n"
            "## Dependencies\nblocked-by: #4\nblocks: #6\n\n"
            "**Note:** Requires ≥7 days of stored data from Issue #4."
        ),
    },
    {
        "title": "Issue #6: Phase 2 — Paper trader + risk controls",
        "body": (
            "## Goal\nBuild risk.py, portfolio.py, trader.py, learner.py. Full paper trading loop.\n\n"
            "## Acceptance criteria\n"
            "- [ ] `paper_trade --duration 15m` runs end-to-end with session summary\n"
            "- [ ] Telegram notification sent on session complete\n"
            "- [ ] Charts saved to logs/charts/\n"
            "- [ ] All risk control tests pass\n"
            "- [ ] Learner adapts params after 10 sessions\n\n"
            "## Dates\nStart: 2026-06-01\nDue: 2026-06-14\n\n"
            "## Dependencies\nblocked-by: #5\nblocks: #7"
        ),
    },
    {
        "title": "Issue #7: Capital analysis + final recommendation",
        "body": (
            "## Goal\nComplete capital analysis. Write final recommendation.\n\n"
            "## Acceptance criteria\n"
            "- [ ] RESEARCH.md Section 12 fully written with fee math\n"
            "- [ ] Final verdict printed: DO NOT TRADE / PAPER TRADE ONLY / MANUAL ORDER-TICKET\n"
            "- [ ] reschedule.py tested end-to-end\n\n"
            "## Dates\nStart: 2026-06-15\nDue: 2026-06-28\n\n"
            "## Dependencies\nblocked-by: #6"
        ),
    },
]

if not TOKEN or not REPO:
    print("ERROR: Set GITHUB_TOKEN and GITHUB_REPO in .env first.")
    raise SystemExit(1)

for issue in ISSUES:
    resp = requests.post(
        f"https://api.github.com/repos/{REPO}/issues",
        headers=HEADERS,
        json={"title": issue["title"], "body": issue["body"]},
    )
    print(f"Created: {issue['title']} — {resp.status_code}")

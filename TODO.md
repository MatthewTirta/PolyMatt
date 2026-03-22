# PolyMatt — Task Tracker

GitHub issues are created in Issue #17. Track them here locally too.

---

- [ ] **Issue #1 — Research + scaffold** (2026-03-22 → 2026-04-05)
  Complete RESEARCH.md with 12 cited sections; repo scaffold in place.
  _Blocks: #2_

- [ ] **Issue #2 — BTC market discovery** (2026-04-06 → 2026-04-19)
  `polymatt/market/client.py` + `discover.py` + CLI `fetch_markets.py`.
  _Blocks: #3_

- [ ] **Issue #3 — Live orderbook feed** (2026-04-20 → 2026-05-03)
  `polymatt/data/feed.py` + WebSocket reconnection + `watch_orderbook.py`.
  _Blocks: #4_

- [ ] **Issue #4 — Storage + CLI** (2026-05-04 → 2026-05-17)
  `polymatt/data/storage.py` + `btc_price.py` + SQLite persistence for all data.
  _Blocks: #5_

- [ ] **Issue #5 — Strategy + backtest** (2026-05-18 → 2026-05-31)
  `polymatt/strategy/baseline.py` + `learner.py` + `backtest/engine.py` + 1,000-run harness.
  Requires ≥7 days of stored data from Issue #4.
  _Blocks: #6_

- [ ] **Issue #6 — Paper trader** (2026-06-01 → 2026-06-14)
  `polymatt/paper_trader/risk.py` + `portfolio.py` + `trader.py` + charts + Telegram.
  _Blocks: #7_

- [ ] **Issue #7 — Capital analysis** (2026-06-15 → 2026-06-28)
  Full capital analysis: funding minimums, fees, slippage, practical minimum bankroll.
  Final recommendation: do not trade / paper trade only / manual order-ticket only.

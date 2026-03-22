# PolyMatt — Polymarket Research

> **Status:** Placeholder — to be completed during Issue #1.
> Every claim must include a URL citation to official docs, help center, or SDK source. No assumptions.

---

## 1. Polymarket Market Structure

TODO: research and cite

- What is a prediction market?
- How does CLOB (Central Limit Order Book) work on Polymarket?
- How are YES/NO shares priced?

---

## 2. BTC Market Types on Polymarket

TODO: research and cite

- What kinds of BTC markets exist (price targets, weekly close, end-of-month)?
- How do they resolve?
- Typical durations?

---

## 3. Recurring BTC Markets

TODO: research and cite

- Which BTC markets reset weekly/monthly?
- Which can be traded repeatedly?

---

## 4. Wallet & Auth Flow

TODO: research and cite

- How does Polymarket use a Polygon wallet (Magic.link or Metamask)?
- What does the API key flow look like for the CLOB API?

---

## 5. Funding & Bridge Flow

TODO: research and cite

- How is USDC deposited?
- Which bridge is used (Polygon PoS bridge)?
- What is the minimum deposit?

---

## 6. Fees

TODO: research and cite

- Taker fee (~2%)?
- Maker fee (0%)?
- Any withdrawal fees?

---

## 7. Order Types

TODO: research and cite

- Market orders, limit orders?
- GTC vs FOK?

---

## 8. Orderbook Fields

TODO: research and cite

- What fields does the CLOB API return for bids, asks, and trades?

---

## 9. WebSocket Channels

TODO: research and cite

- Available feed subscriptions and their message formats?

---

## 10. Rate Limits

TODO: research and cite

- Requests per second/minute for REST and WebSocket?

---

## 11. Geographic Restrictions

TODO: research and cite

- Which countries are blocked?
- Is it trading only, or also API access?

---

## 12. BTC Lag Hypothesis

TODO: research and cite

- *Hypothesis (not fact):* Does Polymarket BTC odds lag spot price?
- On what timeframe?
- Is there published evidence or prior art?
- Must be validated empirically — see `polymatt/strategy/baseline.py::validate_lag_hypothesis()`
- Reject hypothesis if median lag < 30 seconds across at least 20 measured events

"""
trader.py — Paper trade execution engine.

Evaluates signals on live data and simulates trade execution.
Never touches real money. All trades are stored in SQLite.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from polymatt import config
from polymatt.market.models import Orderbook, PaperTrade
from polymatt.strategy.baseline import StrategyParams, evaluate_signal
from polymatt.strategy.learner import Learner
from polymatt.paper_trader.portfolio import Portfolio
from polymatt.paper_trader.risk import make_risk_checker_from_config
from polymatt.data.storage import save_paper_trade, get_trade_count_last_hour, get_btc_prices_since, get_trades_since
from polymatt.notifications import send as notify

logger = logging.getLogger(__name__)

TAKER_FEE = 0.02
SLIPPAGE = 0.005
TRADE_SIZE_USD = 20.0   # fixed position size per trade


class PaperTrader:
    """
    Runs the paper trading loop.
    Evaluates signals every 30 seconds and simulates execution.
    """

    def __init__(self, condition_id: str, learner: Optional[Learner] = None):
        self.condition_id = condition_id
        self.learner = learner
        self.params = learner.get_params() if learner else StrategyParams()
        self.portfolio = Portfolio(config.PAPER_BANKROLL_USD)
        self.risk = make_risk_checker_from_config(config.PAPER_BANKROLL_USD)
        self.last_orderbook: Optional[Orderbook] = None
        self.open_trades: list = []
        self.session_num = 0

    def on_orderbook(self, ob: Orderbook):
        """Called by feed.py whenever a new orderbook snapshot arrives."""
        self.last_orderbook = ob

    async def run_loop(self, stop_event: asyncio.Event):
        """Main loop: evaluate signals every 30 seconds until stop_event fires."""
        while not stop_event.is_set():
            await asyncio.sleep(30)
            if self.last_orderbook:
                self._evaluate_and_trade()

    def _evaluate_and_trade(self):
        ob = self.last_orderbook
        if ob is None:
            return

        # Get real BTC spot price change from stored CoinGecko data.
        # This must match what the backtest engine uses so results are comparable.
        window_seconds = self.params.momentum_window_min * 60
        window_prices = get_btc_prices_since(
            datetime.utcnow() - timedelta(seconds=window_seconds)
        )
        if len(window_prices) < 2:
            return  # not enough BTC data yet — skip this evaluation
        btc_change = ((window_prices[-1][1] - window_prices[0][1]) / window_prices[0][1]) * 100

        recent = get_trades_since(self.condition_id,
                                   datetime.utcnow() - timedelta(minutes=10))

        signal = evaluate_signal(self.condition_id, recent, ob,
                                  btc_change_pct=btc_change, params=self.params)
        if signal is None:
            return

        open_pos = len(self.open_trades)
        spread = ob.spread_pct() or 0
        liq = sum(b.size for b in ob.bids[:3]) * (ob.best_bid() or 0)

        allowed, reason = self.risk.can_trade(
            size_usd=TRADE_SIZE_USD,
            spread_pct=spread,
            liquidity_usd=liq,
            open_positions=open_pos,
            daily_loss=self.portfolio.daily_loss,
        )
        if not allowed:
            logger.info("Trade blocked: %s", reason)
            return

        entry = ob.best_ask() if signal.direction == "YES" else ob.best_bid()
        if entry is None:
            return

        trade = PaperTrade(
            condition_id=self.condition_id,
            direction=signal.direction,
            entry_price=entry,
            size_usd=TRADE_SIZE_USD,
            entry_time=datetime.utcnow(),
            reason=signal.reason,
        )
        self.open_trades.append(trade)
        logger.info("Paper trade entered: %s @ %.3f — %s", signal.direction, entry, signal.reason)

        # Immediately simulate exit (simplified: exit after 5 min at last price + small move)
        exit_price = entry + (0.015 * (1 if signal.direction == "YES" else -1))
        gross = (exit_price - entry) * TRADE_SIZE_USD
        net = gross - (TRADE_SIZE_USD * TAKER_FEE) - (TRADE_SIZE_USD * SLIPPAGE)
        trade.exit_price = exit_price
        trade.exit_time = datetime.utcnow()
        trade.pnl = net
        self.portfolio.record_closed_trade(net)
        self.open_trades.remove(trade)
        save_paper_trade(trade)

    def close_session(self) -> dict:
        """Close all open positions and return session summary."""
        ob = self.last_orderbook
        for trade in list(self.open_trades):
            price = (ob.best_ask() or trade.entry_price) if ob else trade.entry_price
            pnl = (price - trade.entry_price) * trade.size_usd
            pnl -= trade.size_usd * (TAKER_FEE + SLIPPAGE)
            trade.exit_price = price
            trade.exit_time = datetime.utcnow()
            trade.pnl = pnl
            self.portfolio.record_closed_trade(pnl)
            save_paper_trade(trade)
        self.open_trades.clear()

        summary = self.portfolio.summary()
        if self.learner:
            self.learner.record_session(
                win_rate=self.portfolio.win_rate() / 100,
                params_used=self.params,
                trades=[],
            )
        return summary

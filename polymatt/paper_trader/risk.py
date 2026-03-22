"""
risk.py — Enforce all risk controls before any paper trade.

These rules are FIXED — the adaptive learner cannot change them.
They are the safety guardrails that protect the paper bankroll.
"""
from typing import Tuple


class RiskChecker:
    """
    Check whether a trade is allowed given current risk state.
    All checks run in order; the first failure blocks the trade.
    """

    def __init__(
        self,
        bankroll: float,
        max_risk_per_trade_pct: float,
        max_daily_loss_pct: float,
        max_concurrent_positions: int,
        min_liquidity_usd: float,
        max_spread_pct: float,
        kill_switch: bool,
    ):
        self.bankroll = bankroll
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_concurrent_positions = max_concurrent_positions
        self.min_liquidity_usd = min_liquidity_usd
        self.max_spread_pct = max_spread_pct
        self.kill_switch = kill_switch

    def can_trade(
        self,
        size_usd: float,
        spread_pct: float,
        liquidity_usd: float,
        open_positions: int,
        daily_loss: float,
    ) -> Tuple[bool, str]:
        """
        Returns (True, "ok") if the trade is allowed,
        or (False, "reason") if it is blocked.
        """
        if self.kill_switch:
            return False, "kill switch is ON — all trading halted"

        max_loss = self.bankroll * (self.max_daily_loss_pct / 100)
        if daily_loss >= max_loss:
            return False, f"daily loss limit reached (${daily_loss:.2f} >= ${max_loss:.2f})"

        if open_positions >= self.max_concurrent_positions:
            return False, f"max concurrent positions reached ({open_positions})"

        max_size = self.bankroll * (self.max_risk_per_trade_pct / 100)
        if size_usd > max_size:
            return False, f"trade size ${size_usd:.2f} exceeds max ${max_size:.2f}"

        if spread_pct > self.max_spread_pct:
            return False, f"spread {spread_pct:.1f}% exceeds max {self.max_spread_pct:.1f}%"

        if liquidity_usd < self.min_liquidity_usd:
            return False, f"liquidity ${liquidity_usd:.0f} below min ${self.min_liquidity_usd:.0f}"

        return True, "ok"


def make_risk_checker_from_config(bankroll: float) -> RiskChecker:
    """Create a RiskChecker using values from the .env file."""
    from polymatt import config
    return RiskChecker(
        bankroll=bankroll,
        max_risk_per_trade_pct=config.MAX_RISK_PER_TRADE_PCT,
        max_daily_loss_pct=config.MAX_DAILY_LOSS_PCT,
        max_concurrent_positions=config.MAX_CONCURRENT_POSITIONS,
        min_liquidity_usd=config.MIN_LIQUIDITY_USD,
        max_spread_pct=config.MAX_SPREAD_PCT,
        kill_switch=config.KILL_SWITCH,
    )

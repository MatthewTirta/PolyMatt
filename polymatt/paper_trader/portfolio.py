"""
portfolio.py — Track paper trading PnL, wins, losses, and drawdown.
"""


class Portfolio:
    """Tracks the financial state of a paper trading session."""

    def __init__(self, starting_bankroll: float):
        self.starting_bankroll = starting_bankroll
        self.current_bankroll = starting_bankroll
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0          # biggest single-session loss seen
        self.daily_loss = 0.0            # total loss today (resets each session)
        self._peak_bankroll = starting_bankroll

    def record_closed_trade(self, pnl: float):
        """Update all stats after a trade closes."""
        self.total_pnl += pnl
        self.current_bankroll += pnl

        if pnl > 0:
            self.wins += 1
            self._peak_bankroll = max(self._peak_bankroll, self.current_bankroll)
        else:
            self.losses += 1
            self.daily_loss += abs(pnl)
            drawdown = self._peak_bankroll - self.current_bankroll
            self.max_drawdown = max(self.max_drawdown, drawdown)

    def win_rate(self) -> float:
        """Win rate as a percentage (0–100). Returns 0 if no trades."""
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return (self.wins / total) * 100

    def summary(self) -> dict:
        """Return a dict of all stats for printing or saving."""
        return {
            "wins": self.wins,
            "losses": self.losses,
            "win_rate_pct": round(self.win_rate(), 1),
            "total_pnl": round(self.total_pnl, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "daily_loss": round(self.daily_loss, 2),
            "current_bankroll": round(self.current_bankroll, 2),
        }

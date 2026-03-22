"""
learner.py — Adaptive parameter tuner.

After every 10 sessions, adjusts strategy parameters towards what worked best.
If the update makes things worse, it automatically rolls back.
All state is saved to logs/learning_state.json — readable, never hidden.
"""
import json
import logging
import os
from dataclasses import asdict
from polymatt.strategy.baseline import StrategyParams

logger = logging.getLogger(__name__)


class Learner:
    """
    Tracks session history and adjusts strategy parameters over time.
    Uses a simple rule: after 10 sessions, weight recent profitable params higher.
    """

    def __init__(self, state_file: str = "logs/learning_state.json"):
        self.state_file = state_file
        self.sessions = []          # list of {win_rate, params, trades}
        self.param_versions = []    # full history of param sets
        self.rollback_count = 0
        self._current_params = StrategyParams()
        self._prev_params = StrategyParams()
        self._load_state()

    def _load_state(self):
        """Load saved state from disk if it exists."""
        try:
            with open(self.state_file) as f:
                data = json.load(f)
                self.sessions = data.get("sessions", [])
                self.param_versions = data.get("param_versions", [])
                self.rollback_count = data.get("rollback_count", 0)
                if self.param_versions:
                    latest = self.param_versions[-1]["params"]
                    self._current_params = StrategyParams(**latest)
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # first run — start fresh

    def _save_state(self):
        """Write current state to disk."""
        dir_name = os.path.dirname(self.state_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        data = {
            "sessions": self.sessions[-100:],  # keep last 100 for disk efficiency
            "param_versions": self.param_versions,
            "rollback_count": self.rollback_count,
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_params(self) -> StrategyParams:
        """Return the current best parameters."""
        return self._current_params

    def record_session(self, win_rate: float, params_used: StrategyParams, trades: list):
        """
        Record a completed session. Every 10 sessions, attempt a parameter update.
        """
        self.sessions.append({
            "win_rate": win_rate,
            "params": asdict(params_used),
            "trades": trades,  # stored for future per-trade analysis
        })

        if len(self.sessions) % 10 == 0:
            self._attempt_update()
            self._save_state()

    def _attempt_update(self):
        """
        Calculate new params from recent sessions.
        Roll back if the new params perform worse than the previous set.
        """
        recent = self.sessions[-10:]
        prev_10 = self.sessions[-20:-10] if len(self.sessions) >= 20 else []

        recent_avg_wr = sum(s["win_rate"] for s in recent) / len(recent)
        prev_avg_wr = sum(s["win_rate"] for s in prev_10) / len(prev_10) if prev_10 else recent_avg_wr

        # Rollback if performance got worse.
        # We allow a 5% (0.05) tolerance so we don't roll back on random noise —
        # only roll back if the drop is meaningful (e.g. 65% → 58%).
        if prev_10 and recent_avg_wr < prev_avg_wr - 0.05:
            logger.info("Win rate dropped %.1f%% → %.1f%%, rolling back params",
                        prev_avg_wr * 100, recent_avg_wr * 100)
            self.rollback_count += 1
            self._current_params = self._prev_params
            # Remove the bad param set so _load_state restores the good params on restart
            if self.param_versions:
                self.param_versions.pop()
            return

        # Calculate new params: weighted average of profitable sessions
        profitable = [s for s in recent if s["win_rate"] > 0.5]
        if not profitable:
            return

        self._prev_params = self._current_params

        def weighted_avg(key):
            """Average the param across profitable sessions, weighted by win rate."""
            vals = [s["params"][key] * s["win_rate"] for s in profitable]
            weights = [s["win_rate"] for s in profitable]
            return sum(vals) / sum(weights)

        bounds = StrategyParams.BOUNDS

        def clamp(key, val):
            lo, hi = bounds[key]
            return max(lo, min(hi, val))

        new_params = StrategyParams(
            momentum_window_min=int(clamp("momentum_window_min",
                                          weighted_avg("momentum_window_min"))),
            entry_confidence_pct=clamp("entry_confidence_pct",
                                        weighted_avg("entry_confidence_pct")),
            spread_threshold_pct=clamp("spread_threshold_pct",
                                        weighted_avg("spread_threshold_pct")),
            min_liquidity_usd=clamp("min_liquidity_usd",
                                     weighted_avg("min_liquidity_usd")),
            cooldown_after_losses_min=int(clamp("cooldown_after_losses_min",
                                                 weighted_avg("cooldown_after_losses_min"))),
        )

        self.param_versions.append({
            "session_count": len(self.sessions),
            "win_rate": round(recent_avg_wr, 3),
            "params": asdict(new_params),
        })

        logger.info("Params updated. Win rate: %.1f%%. spread_threshold: %.2f → %.2f",
                    recent_avg_wr * 100,
                    self._current_params.spread_threshold_pct,
                    new_params.spread_threshold_pct)
        self._current_params = new_params

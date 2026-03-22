"""
charts.py — Generate matplotlib charts after each session.
Saves PNGs to logs/charts/.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
CHARTS_DIR = Path("logs/charts")


def save_session_pnl_chart(session_num: int, pnl_values: list):
    """Save a PnL-over-time chart for one session."""
    try:
        import matplotlib.pyplot as plt
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(pnl_values, color="green" if pnl_values[-1] >= 0 else "red")
        ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_title(f"Session #{session_num:03d} — PnL")
        ax.set_xlabel("Trade #")
        ax.set_ylabel("Cumulative PnL ($)")
        path = CHARTS_DIR / f"session_{session_num:03d}_pnl.png"
        fig.savefig(str(path), dpi=100, bbox_inches="tight")
        plt.close(fig)
        return str(path)
    except Exception as e:
        logger.warning("Chart generation failed (non-fatal): %s", e)
        return None


def save_winrate_trend_chart(session_win_rates: list):
    """Save a chart showing win rate improvement across all sessions."""
    try:
        import matplotlib.pyplot as plt
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(session_win_rates, color="blue")
        ax.axhline(50, color="red", linestyle="--", linewidth=0.8, label="Break-even")
        ax.set_title("Win Rate Trend Across Sessions")
        ax.set_xlabel("Session #")
        ax.set_ylabel("Win Rate (%)")
        ax.legend()
        path = CHARTS_DIR / "winrate_trend.png"
        fig.savefig(str(path), dpi=100, bbox_inches="tight")
        plt.close(fig)
        return str(path)
    except Exception as e:
        logger.warning("Chart generation failed (non-fatal): %s", e)
        return None


def save_parameter_evolution_chart(param_versions: list):
    """
    Save a chart showing how each adaptive parameter changed over time.
    param_versions is a list of dicts from learning_state.json:
      [{"session_count": N, "params": {"spread_threshold_pct": X, ...}}, ...]
    """
    try:
        import matplotlib.pyplot as plt
        if not param_versions:
            return None
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        sessions = [v["session_count"] for v in param_versions]
        param_keys = ["spread_threshold_pct", "entry_confidence_pct",
                      "momentum_window_min", "min_liquidity_usd"]

        fig, axes = plt.subplots(len(param_keys), 1, figsize=(10, 3 * len(param_keys)))
        for ax, key in zip(axes, param_keys):
            values = [v["params"].get(key, 0) for v in param_versions]
            ax.plot(sessions, values, marker="o", markersize=3)
            ax.set_title(f"Parameter: {key}")
            ax.set_xlabel("Session #")
            ax.set_ylabel("Value")

        fig.suptitle("Adaptive Parameter Evolution", fontsize=14)
        fig.tight_layout()
        path = CHARTS_DIR / "parameter_evolution.png"
        fig.savefig(str(path), dpi=100, bbox_inches="tight")
        plt.close(fig)
        return str(path)
    except Exception as e:
        logger.warning("Parameter evolution chart failed (non-fatal): %s", e)
        return None

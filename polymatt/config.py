"""
config.py — Load and validate all settings from the .env file.

Every script calls check_kill_switch() at the top before doing anything.
If KILL_SWITCH=true, the program exits immediately with a clear message.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()  # reads .env file in the current directory


def _optional(key: str, default: str = "") -> str:
    """Get an env var. Returns default if not set."""
    return os.getenv(key, default)


# ── Polymarket ───────────────────────────────────────────────────────────────
POLYMARKET_HOST = _optional("POLYMARKET_HOST", "https://clob.polymarket.com")
POLYMARKET_WS_HOST = _optional(
    "POLYMARKET_WS_HOST", "wss://ws-subscriptions-clob.polymarket.com/ws"
)
POLYMARKET_PRIVATE_KEY = _optional("POLYMARKET_PRIVATE_KEY")
POLYMARKET_API_KEY = _optional("POLYMARKET_API_KEY")
POLYMARKET_API_SECRET = _optional("POLYMARKET_API_SECRET")
POLYMARKET_API_PASSPHRASE = _optional("POLYMARKET_API_PASSPHRASE")

# ── Telegram (optional — silently skipped if blank) ──────────────────────────
TELEGRAM_BOT_TOKEN = _optional("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _optional("TELEGRAM_CHAT_ID")

# ── GitHub (needed only for scripts/reschedule.py) ───────────────────────────
GITHUB_TOKEN = _optional("GITHUB_TOKEN")
GITHUB_REPO = _optional("GITHUB_REPO")

# ── Risk controls ────────────────────────────────────────────────────────────
MAX_RISK_PER_TRADE_PCT = float(_optional("MAX_RISK_PER_TRADE_PCT", "2"))
MAX_DAILY_LOSS_PCT = float(_optional("MAX_DAILY_LOSS_PCT", "10"))
MAX_CONCURRENT_POSITIONS = int(_optional("MAX_CONCURRENT_POSITIONS", "3"))
MIN_LIQUIDITY_USD = float(_optional("MIN_LIQUIDITY_USD", "500"))
MAX_SPREAD_PCT = float(_optional("MAX_SPREAD_PCT", "5"))
COOLDOWN_AFTER_LOSSES_MIN = int(_optional("COOLDOWN_AFTER_LOSSES_MIN", "10"))
KILL_SWITCH = _optional("KILL_SWITCH", "false").lower() == "true"

# ── Paper trading ────────────────────────────────────────────────────────────
PAPER_BANKROLL_USD = float(_optional("PAPER_BANKROLL_USD", "1000"))

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = _optional("LOG_LEVEL", "INFO")


def check_kill_switch():
    """
    Call this at the start of every script.
    If KILL_SWITCH=true in .env, exits immediately with a clear message.
    """
    if KILL_SWITCH:
        print("[PolyMatt] KILL SWITCH IS ON — halting immediately.")
        print("  -> Set KILL_SWITCH=false in your .env file to resume.")
        sys.exit(1)  # non-zero exit code signals abnormal halt to shell/CI

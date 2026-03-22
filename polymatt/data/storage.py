"""
storage.py — Save and load market data using SQLite.

SQLite is a simple database stored as a single file (data/polymatt.db).
No server needed — Python has built-in support for it.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from polymatt.market.models import Trade, Orderbook, OrderbookLevel, PaperTrade

logger = logging.getLogger(__name__)
DB_PATH = Path("data/polymatt.db")


def get_connection() -> sqlite3.Connection:
    """Open the database (creates the file if it doesn't exist yet)."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # lets us use column names like row["price"]
    return conn


def init_db():
    """Create all tables. Safe to call multiple times — won't delete existing data."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            condition_id TEXT    NOT NULL,
            timestamp    TEXT    NOT NULL,
            price        REAL    NOT NULL,
            size         REAL    NOT NULL,
            side         TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orderbooks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            condition_id TEXT    NOT NULL,
            timestamp    TEXT    NOT NULL,
            best_bid     REAL,
            best_ask     REAL,
            spread_pct   REAL,
            raw_json     TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            condition_id TEXT    NOT NULL,
            direction    TEXT    NOT NULL,
            entry_price  REAL    NOT NULL,
            size_usd     REAL    NOT NULL,
            entry_time   TEXT    NOT NULL,
            exit_price   REAL,
            exit_time    TEXT,
            pnl          REAL,
            reason       TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_trades_cond ON trades(condition_id);
        CREATE INDEX IF NOT EXISTS idx_trades_ts   ON trades(timestamp);
        CREATE INDEX IF NOT EXISTS idx_ob_cond     ON orderbooks(condition_id);
    """)
    conn.commit()
    conn.close()
    logger.info("Database ready at %s", DB_PATH)


def save_trade(trade: Trade):
    """Save one trade event to the database."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO trades (condition_id, timestamp, price, size, side) VALUES (?,?,?,?,?)",
        (trade.condition_id, trade.timestamp.isoformat(), trade.price, trade.size, trade.side),
    )
    conn.commit()
    conn.close()


def save_orderbook(ob: Orderbook):
    """Save an orderbook snapshot to the database."""
    raw = {
        "bids": [{"price": b.price, "size": b.size} for b in ob.bids],
        "asks": [{"price": a.price, "size": a.size} for a in ob.asks],
    }
    conn = get_connection()
    conn.execute(
        """INSERT INTO orderbooks
           (condition_id, timestamp, best_bid, best_ask, spread_pct, raw_json)
           VALUES (?,?,?,?,?,?)""",
        (ob.condition_id, ob.timestamp.isoformat(),
         ob.best_bid(), ob.best_ask(), ob.spread_pct(), json.dumps(raw)),
    )
    conn.commit()
    conn.close()


def save_paper_trade(pt: PaperTrade):
    """Save or update a paper trade."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO paper_trades
           (condition_id, direction, entry_price, size_usd, entry_time,
            exit_price, exit_time, pnl, reason)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (pt.condition_id, pt.direction, pt.entry_price, pt.size_usd,
         pt.entry_time.isoformat(),
         pt.exit_price,
         pt.exit_time.isoformat() if pt.exit_time else None,
         pt.pnl, pt.reason),
    )
    conn.commit()
    conn.close()


def get_trades_since(condition_id: str, since: datetime) -> list:
    """Return all trades for a market recorded after `since`."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM trades WHERE condition_id=? AND timestamp>=? ORDER BY timestamp ASC",
        (condition_id, since.isoformat()),
    ).fetchall()
    conn.close()
    return [
        Trade(
            condition_id=r["condition_id"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            price=r["price"], size=r["size"], side=r["side"],
        )
        for r in rows
    ]


def get_orderbooks_since(condition_id: str, since: datetime) -> list:
    """Return all orderbook snapshots for a market recorded after `since`."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orderbooks WHERE condition_id=? AND timestamp>=? ORDER BY timestamp ASC",
        (condition_id, since.isoformat()),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        raw = json.loads(r["raw_json"])
        ob = Orderbook(
            condition_id=r["condition_id"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            bids=[OrderbookLevel(b["price"], b["size"]) for b in raw["bids"]],
            asks=[OrderbookLevel(a["price"], a["size"]) for a in raw["asks"]],
        )
        result.append(ob)
    return result


def get_trade_count_last_hour(condition_id: str) -> int:
    """Count trades recorded in the last 60 minutes."""
    since = datetime.utcnow() - timedelta(hours=1)
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE condition_id=? AND timestamp>=?",
        (condition_id, since.isoformat()),
    ).fetchone()[0]
    conn.close()
    return count

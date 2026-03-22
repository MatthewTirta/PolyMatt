"""
feed.py — Connect to Polymarket's live WebSocket feed.

Streams orderbook and trade events in real time.
Automatically reconnects if the connection drops (up to 5 attempts).
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Callable
import websockets
from polymatt import config
from polymatt.market.models import Trade, Orderbook, OrderbookLevel
from polymatt.data.storage import save_trade, save_orderbook

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_DELAYS = [5, 10, 20, 40, 80]  # seconds between reconnect attempts


async def _connect_and_stream(
    condition_id: str,
    on_trade: Optional[Callable] = None,
    on_orderbook: Optional[Callable] = None,
    stop_event: Optional[asyncio.Event] = None,
):
    """
    Open one WebSocket connection and stream events until stop_event is set.
    Raises an exception if the connection drops — caller handles reconnect.
    """
    subscribe_msg = json.dumps({
        "auth": {},
        "markets": [condition_id],
        "assets_ids": [],
        "type": "market",
    })

    async with websockets.connect(config.POLYMARKET_WS_HOST) as ws:
        await ws.send(subscribe_msg)
        logger.info("WebSocket connected for market %s", condition_id)

        while True:
            if stop_event and stop_event.is_set():
                return  # clean exit

            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
            except asyncio.TimeoutError:
                await ws.ping()  # keep-alive
                continue

            msg = json.loads(raw)
            msg_type = msg.get("event_type", "")

            if msg_type == "trade":
                trade = Trade(
                    condition_id=condition_id,
                    timestamp=datetime.utcnow(),
                    price=float(msg.get("price", 0)),
                    size=float(msg.get("size", 0)),
                    side=msg.get("outcome", "YES"),
                )
                save_trade(trade)
                if on_trade:
                    on_trade(trade)

            elif msg_type in ("book", "price_change"):
                bids = [OrderbookLevel(float(b["price"]), float(b["size"]))
                        for b in msg.get("bids", [])]
                asks = [OrderbookLevel(float(a["price"]), float(a["size"]))
                        for a in msg.get("asks", [])]
                ob = Orderbook(
                    condition_id=condition_id,
                    timestamp=datetime.utcnow(),
                    bids=bids,
                    asks=asks,
                )
                save_orderbook(ob)
                if on_orderbook:
                    on_orderbook(ob)


async def stream_market(
    condition_id: str,
    on_trade: Optional[Callable] = None,
    on_orderbook: Optional[Callable] = None,
    stop_event: Optional[asyncio.Event] = None,
    notify_fn: Optional[Callable] = None,
    close_positions_fn: Optional[Callable] = None,
):
    """
    Stream one market's live data with automatic reconnection.

    If the connection drops, retries up to 5 times with increasing wait times.
    If all retries fail:
      - calls close_positions_fn() to close all open paper positions at last known price
      - sends a Telegram notification via notify_fn
      - logs the error and exits cleanly
    """
    for attempt in range(MAX_RETRIES):
        try:
            await _connect_and_stream(condition_id, on_trade, on_orderbook, stop_event)
            return  # clean exit
        except Exception as e:
            delay = RETRY_DELAYS[attempt]
            logger.warning(
                "WebSocket error (attempt %d/%d): %s. Retrying in %ds...",
                attempt + 1, MAX_RETRIES, e, delay,
            )
            await asyncio.sleep(delay)

    # All retries exhausted — close positions before exiting
    error_msg = (
        f"[PolyMatt] WebSocket permanently disconnected after {MAX_RETRIES} attempts."
    )
    logger.error(error_msg)
    if close_positions_fn:
        close_positions_fn()  # close open paper positions at last known price
    if notify_fn:
        notify_fn(error_msg)

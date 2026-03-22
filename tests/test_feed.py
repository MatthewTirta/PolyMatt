# tests/test_feed.py
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from polymatt.data.feed import stream_market


@pytest.mark.asyncio
async def test_reconnects_on_failure():
    """Feed must retry on connection error, not crash immediately."""
    call_count = 0

    async def fake_connect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("simulated drop")
        # On third call, set stop_event so the loop exits cleanly
        args[3].set()  # stop_event is the 4th positional arg

    stop = asyncio.Event()
    with patch("polymatt.data.feed._connect_and_stream", side_effect=fake_connect):
        with patch("polymatt.data.feed.asyncio.sleep", new_callable=AsyncMock):
            await stream_market("test-id", stop_event=stop)
    assert call_count == 3


@pytest.mark.asyncio
async def test_calls_close_positions_fn_on_permanent_failure():
    """close_positions_fn must be called when all retries are exhausted."""
    async def always_fails(*args, **kwargs):
        raise ConnectionError("permanent failure")

    close_called = []
    stop = asyncio.Event()

    with patch("polymatt.data.feed._connect_and_stream", side_effect=always_fails):
        with patch("polymatt.data.feed.asyncio.sleep", new_callable=AsyncMock):
            await stream_market(
                "test-id",
                stop_event=stop,
                close_positions_fn=lambda: close_called.append(True),
            )
    assert len(close_called) == 1

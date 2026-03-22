# tests/test_market.py
from unittest.mock import patch, MagicMock
import pytest
from polymatt.market.client import _with_retry, fetch_markets, fetch_orderbook
from polymatt.market.discover import is_btc_market


@patch("time.sleep")
def test_retry_succeeds_on_third_attempt(mock_sleep):
    """Client should retry up to 3 times and return on success."""
    call_count = 0

    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("temporary failure")
        return "success"

    result = _with_retry(flaky)
    assert result == "success"
    assert call_count == 3
    # 2 failed attempts before success, so sleep should be called twice
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@patch("time.sleep")
def test_retry_raises_after_all_attempts_fail(mock_sleep):
    """Client should raise the last exception after 3 failed attempts."""
    def always_fails():
        raise Exception("permanent failure")

    with pytest.raises(Exception, match="permanent failure"):
        _with_retry(always_fails)
    # 3 failed attempts total, but sleep only after first 2 (not after the final failure)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


def test_fetch_markets_calls_get_markets():
    """fetch_markets should call client.get_markets() via _with_retry."""
    mock_client = MagicMock()
    mock_client.get_markets.return_value = [{"id": "abc"}]
    with patch("time.sleep"):
        result = fetch_markets(mock_client)
    assert result == [{"id": "abc"}]
    mock_client.get_markets.assert_called_once()


def test_fetch_orderbook_calls_get_order_book():
    """fetch_orderbook should GET the CLOB /book endpoint with the token_id."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"bids": [], "asks": []}
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()  # client arg is accepted but not used by the HTTP path
    with patch("polymatt.market.client.requests.get", return_value=mock_response) as mock_get:
        with patch("time.sleep"):
            result = fetch_orderbook(mock_client, "99999token")
    assert result == {"bids": [], "asks": []}
    called_url = mock_get.call_args[0][0]
    assert "99999token" in called_url


def test_btc_market_detected_by_keyword():
    assert is_btc_market("Will BTC close above $70k?") is True
    assert is_btc_market("Will Bitcoin reach $100k by end of year?") is True
    assert is_btc_market("Will ETH flip BTC market cap?") is True  # contains btc


def test_non_btc_market_rejected():
    assert is_btc_market("Will ETH reach $5k?") is False
    assert is_btc_market("Will the Fed cut rates in March?") is False
    assert is_btc_market("Will Solana flip Ethereum?") is False

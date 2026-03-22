# tests/test_preflight.py
import pytest
from unittest.mock import patch, MagicMock
from polymatt.data.preflight import run_preflight


def test_preflight_exits_when_api_unreachable():
    """Score should be 0 and program should exit when API is down."""
    with patch("polymatt.data.preflight.get_btc_markets", side_effect=Exception("timeout")):
        with pytest.raises(SystemExit):
            run_preflight()


def test_preflight_passes_when_all_checks_ok():
    """Score should be 100 when everything is healthy."""
    mock_market = MagicMock()
    mock_market.condition_id = "test-cond"
    mock_ob = {"bids": [{"price": "0.49"}], "asks": [{"price": "0.51"}]}

    with patch("polymatt.data.preflight.get_btc_markets", return_value=[mock_market]):
        with patch("polymatt.data.preflight.get_client", return_value=MagicMock()):
            with patch("polymatt.data.preflight.fetch_orderbook", return_value=mock_ob):
                with patch("polymatt.data.preflight.get_trade_count_last_hour", return_value=100):
                    score = run_preflight()
    assert score == 100


def test_preflight_score_formula():
    """Partial score: API ok (40) + spread ok (30) but no trade history (0) = 70 → exit."""
    mock_market = MagicMock()
    mock_market.condition_id = "test-cond"
    mock_ob = {"bids": [{"price": "0.49"}], "asks": [{"price": "0.51"}]}

    with patch("polymatt.data.preflight.get_btc_markets", return_value=[mock_market]):
        with patch("polymatt.data.preflight.get_client", return_value=MagicMock()):
            with patch("polymatt.data.preflight.fetch_orderbook", return_value=mock_ob):
                with patch("polymatt.data.preflight.get_trade_count_last_hour", return_value=0):
                    with pytest.raises(SystemExit):
                        run_preflight()  # 70 < 80 → should exit

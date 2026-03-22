# tests/test_market.py
from unittest.mock import patch, MagicMock
import pytest
from polymatt.market.client import _with_retry


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


@patch("time.sleep")
def test_retry_raises_after_all_attempts_fail(mock_sleep):
    """Client should raise the last exception after 3 failed attempts."""
    def always_fails():
        raise Exception("permanent failure")

    with pytest.raises(Exception, match="permanent failure"):
        _with_retry(always_fails)

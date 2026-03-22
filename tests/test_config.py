# tests/test_config.py
import os
import importlib
from unittest.mock import patch
import pytest


def test_kill_switch_defaults_to_false(monkeypatch):
    monkeypatch.delenv("KILL_SWITCH", raising=False)
    # We mock load_dotenv so it doesn't re-read a real .env file during reload.
    # Without this, a .env with KILL_SWITCH=true would silently break this test.
    with patch("polymatt.config.load_dotenv"):
        import polymatt.config as cfg
        importlib.reload(cfg)
    assert cfg.KILL_SWITCH is False


def test_kill_switch_true_when_env_set(monkeypatch):
    monkeypatch.setenv("KILL_SWITCH", "true")
    with patch("polymatt.config.load_dotenv"):
        import polymatt.config as cfg
        importlib.reload(cfg)
    assert cfg.KILL_SWITCH is True


def test_check_kill_switch_exits_when_on(monkeypatch):
    monkeypatch.setenv("KILL_SWITCH", "true")
    with patch("polymatt.config.load_dotenv"):
        import polymatt.config as cfg
        importlib.reload(cfg)
    with pytest.raises(SystemExit) as exc_info:
        cfg.check_kill_switch()
    # Must be exit code 1 (non-zero = abnormal halt), not 0 (clean exit)
    assert exc_info.value.code == 1

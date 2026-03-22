# tests/test_config.py
import os
import pytest

def test_kill_switch_defaults_to_false(monkeypatch):
    monkeypatch.delenv("KILL_SWITCH", raising=False)
    # Re-import to pick up patched env
    import importlib
    import polymatt.config as cfg
    importlib.reload(cfg)
    assert cfg.KILL_SWITCH is False

def test_kill_switch_true_when_env_set(monkeypatch):
    monkeypatch.setenv("KILL_SWITCH", "true")
    import importlib
    import polymatt.config as cfg
    importlib.reload(cfg)
    assert cfg.KILL_SWITCH is True

def test_check_kill_switch_exits_when_on(monkeypatch):
    monkeypatch.setenv("KILL_SWITCH", "true")
    import importlib
    import polymatt.config as cfg
    importlib.reload(cfg)
    with pytest.raises(SystemExit):
        cfg.check_kill_switch()

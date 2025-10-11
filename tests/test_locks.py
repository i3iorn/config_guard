import warnings

import pytest

from config_guard.exceptions import ConfigBypassError, ConfigLockedError
from config_guard.locks import LockGuard


def test_lockguard_lock_and_is_locked():
    lg = LockGuard()
    assert lg.is_locked() is False
    lg.lock()
    assert lg.is_locked() is True


def test_lockguard_unlock_with_bypass(monkeypatch):
    lg = LockGuard()
    lg.lock()
    monkeypatch.setenv("ALLOW_CONFIG_BYPASS", "1")
    lg.unlock(_bypass=True)
    assert lg.is_locked() is False


def test_lockguard_unlock_without_bypass_warns():
    lg = LockGuard()
    lg.lock()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        lg.unlock(_bypass=False)
        assert any("Config is still locked" in str(w.message) for w in rec)
        assert lg.is_locked() is True


def test_lockguard_unlock_bypass_without_env_raises(monkeypatch):
    lg = LockGuard()
    lg.lock()
    monkeypatch.delenv("ALLOW_CONFIG_BYPASS", raising=False)
    with pytest.raises(ConfigBypassError):
        lg.unlock(_bypass=True)


def test_lockguard_ensure_unlocked_raises_when_locked():
    lg = LockGuard()
    lg.lock()
    with pytest.raises(ConfigLockedError):
        lg.ensure_unlocked(_bypass=False)


def test_lockguard_ensure_unlocked_bypass_without_env_raises(monkeypatch):
    lg = LockGuard()
    lg.lock()
    monkeypatch.delenv("ALLOW_CONFIG_BYPASS", raising=False)
    with pytest.raises(ConfigBypassError):
        lg.ensure_unlocked(_bypass=True)

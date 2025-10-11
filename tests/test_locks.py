import os

import pytest

from config_guard.exceptions import ConfigLockedError
from config_guard.locks import LockGuard


def test_lockguard_lock_unlock():
    lock = LockGuard()
    os.environ["ALLOW_CONFIG_BYPASS"] = "1"
    lock.lock()
    assert lock.is_locked()
    lock.unlock(_bypass=True)
    assert not lock.is_locked()


def test_lockguard_ensure_unlocked():
    lock = LockGuard()
    lock.lock()
    with pytest.raises(ConfigLockedError):
        lock.ensure_unlocked(_bypass=False)
    # Should not raise if bypass is True and env is set
    os.environ["ALLOW_CONFIG_BYPASS"] = "1"
    lock.ensure_unlocked(_bypass=True)


def test_lockguard_unlock_without_bypass():
    lock = LockGuard()
    lock.lock()
    # Should warn if _bypass is False and locked
    with pytest.warns(UserWarning):
        lock.unlock(_bypass=False)
    assert lock.is_locked()  # Still locked


def test_lockguard_double_lock():
    lock = LockGuard()
    lock.lock()
    # Locking again should not raise, but is_locked stays True
    lock.lock()
    assert lock.is_locked()


def test_lockguard_is_locked_initial():
    lock = LockGuard()
    assert not lock.is_locked()

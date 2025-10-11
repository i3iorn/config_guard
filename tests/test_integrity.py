import pytest

from config_guard.integrity import IntegrityGuard
from config_guard.params import ConfigParam


def test_integrity_guard_basic():
    guard = IntegrityGuard("sha256")
    snap = {ConfigParam(list(ConfigParam)[0]): 1, ConfigParam(list(ConfigParam)[1]): 2}
    guard.update_snapshot(snap)
    assert guard.verify()
    assert isinstance(guard.memory_fingerprint(), str)


def test_integrity_guard_clear():
    guard = IntegrityGuard("sha256")
    snap = {ConfigParam(list(ConfigParam)[0]): 1}
    guard.update_snapshot(snap)
    guard.clear()
    assert guard.last_checksum is None


def test_integrity_guard_bad_algorithm():
    with pytest.raises(ValueError):
        IntegrityGuard("notarealhash")


def test_integrity_guard_seal_and_verify():
    guard = IntegrityGuard("sha256")
    snap = {ConfigParam(list(ConfigParam)[0]): 1}
    guard.update_snapshot(snap)
    checksum = guard.memory_fingerprint()
    sealed = guard.seal_checksum(checksum)
    assert isinstance(sealed, str)
    # Tamper with checksum
    assert not guard.seal_checksum("bad") == sealed


def test_integrity_guard_start_checker_and_stop():
    guard = IntegrityGuard("sha256")
    called = []

    def on_violation(msg):
        called.append(msg)

    def is_torn_down():
        return True

    guard.start_checker(is_torn_down=is_torn_down, on_violation=on_violation)
    guard.clear()
    # Should not call on_violation since is_torn_down returns True
    assert called == []

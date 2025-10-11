import time

import pytest

from config_guard.integrity import IntegrityGuard


def test_integrity_init_and_update_and_verify(monkeypatch):
    ig = IntegrityGuard("sha256")
    assert ig.last_checksum is None
    assert ig.verify() is False

    ig.update_snapshot({"a": 1})
    first = ig.last_checksum
    assert isinstance(first, str)
    assert ig.verify() is True

    # Changing snapshot changes checksum
    ig.update_snapshot({"a": 2})
    assert ig.last_checksum != first


def test_integrity_init_invalid_algo():
    with pytest.raises(ValueError):
        IntegrityGuard("abc123")


def test_integrity_seal_checksum(monkeypatch):
    ig = IntegrityGuard()
    ig.update_snapshot({"a": 1})

    # With no key, seal returns input
    monkeypatch.delenv("CONFIG_HMAC_KEY", raising=False)
    sealed1 = ig.seal_checksum("deadbeef")
    assert sealed1 == "deadbeef"

    # With key set, returns an HMAC and should differ from input
    monkeypatch.setenv("CONFIG_HMAC_KEY", "secret")
    sealed2 = ig.seal_checksum("deadbeef")
    assert isinstance(sealed2, str)
    assert sealed2 != "deadbeef"


def test_integrity_memory_fingerprint_is_stable_type():
    ig = IntegrityGuard()
    ig.update_snapshot({"x": 42})
    fp = ig.memory_fingerprint()
    assert isinstance(fp, str)


def test_integrity_clear_and_verify():
    ig = IntegrityGuard()
    ig.update_snapshot({"x": 1})
    assert ig.verify() is True
    ig.clear()
    assert ig.verify() is False


def test_integrity_start_checker_and_join():
    ig = IntegrityGuard()
    ig.update_snapshot({"x": 1})

    calls = []

    def is_torn_down():
        # Make the loop exit immediately so join returns quickly
        calls.append(1)
        return True

    triggered = []

    def on_violation(msg):
        triggered.append(msg)

    ig.start_checker(is_torn_down=is_torn_down, on_violation=on_violation)
    ig.join()
    assert not triggered


def test_integrity_start_checker_triggers_on_violation():
    ig = IntegrityGuard()
    # set stale checksum that won't match
    ig._last_snapshot = {"a": 1}  # type: ignore[attr-defined]
    ig._last_checksum = "not-matching"  # type: ignore[attr-defined]

    called = []

    def is_torn_down():
        called.append(1)
        # allow exactly one loop iteration, then signal teardown
        return len(called) > 1

    violations = []

    def on_violation(msg):
        violations.append(msg)

    ig.start_checker(is_torn_down=is_torn_down, on_violation=on_violation)
    # Let the background thread run once
    time.sleep(0.05)
    assert violations and "integrity violation".lower() in violations[0].lower()

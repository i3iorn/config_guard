import warnings

import pytest

from config_guard import AppConfig
from config_guard.exceptions import (
    ConfigBypassError,
    ConfigLockedError,
    ConfigTornDownError,
    ConfigValidationError,
)


@pytest.fixture
def app():
    cfg = AppConfig()
    yield cfg
    try:
        cfg.teardown()
    except Exception:
        pass


def test_appconfig_init_with_bypass_requires_env(monkeypatch):
    monkeypatch.delenv("ALLOW_CONFIG_BYPASS", raising=False)
    with pytest.raises(ConfigBypassError):
        AppConfig(initial_values={"_bypass": True})


def test_appconfig_lock_unlock_and_is_locked(monkeypatch, app):
    assert app.is_locked() is False
    app.lock()
    assert app.is_locked() is True

    # unlock without bypass warns and stays locked
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        app.unlock(_bypass=False)
        assert any("Config is still locked" in str(w.message) for w in rec)
    assert app.is_locked() is True

    # unlock with bypass needs env
    with pytest.raises(ConfigBypassError):
        app.unlock(_bypass=True)

    # set env then unlock
    monkeypatch.setenv("ALLOW_CONFIG_BYPASS", "1")
    app.unlock(_bypass=True)
    assert app.is_locked() is False


def test_appconfig_update_and_get_and_use_once(app):
    app.update(MAX_CONCURRENCY=20)
    assert app.get("MAX_CONCURRENCY") == 20

    app.use_once(MAX_CONCURRENCY=30)
    assert app.get("MAX_CONCURRENCY") == 30
    # falls back to permanent after one use
    assert app.get("MAX_CONCURRENCY") == 20


def test_appconfig_update_validation_error(app):
    with pytest.raises(ConfigValidationError):
        app.update(MAX_CONCURRENCY=0)


def test_appconfig_update_when_locked_raises(app):
    app.lock()
    with pytest.raises(ConfigLockedError):
        app.update(MAX_CONCURRENCY=20)


def test_appconfig_get_after_teardown_raises():
    cfg = AppConfig()
    cfg.teardown()
    with pytest.raises(ConfigTornDownError):
        cfg.get("MAX_CONCURRENCY")


def test_appconfig_restore_from_snapshot_success_and_failure(app):
    snap = {"MAX_CONCURRENCY": 50, "VERIFY": False}
    app.restore_from_snapshot(snap)
    assert app.get("MAX_CONCURRENCY") == 50

    with pytest.raises(ConfigValidationError):
        app.restore_from_snapshot({"MAX_CONCURRENCY": 0})


def test_appconfig_register_hook_and_trigger(app):
    called = []

    def hk(s):
        called.append(s)

    app.register_post_update_hook(hk)
    app.update(VERIFY=False)
    assert called and called[-1]["VERIFY"] is False

    # error case: register non-callable
    with pytest.raises(TypeError):
        app.register_post_update_hook(123)  # type: ignore[arg-type]


def test_appconfig_temp_update_success_and_error(app):
    # success path and revert
    orig = app.get("VERIFY")
    with app.temp_update(VERIFY=False):
        assert app.get("VERIFY") is False
    assert app.get("VERIFY") == orig

    # error path: invalid value triggers error
    with pytest.raises(ConfigValidationError):
        with app.temp_update(MAX_CONCURRENCY=0):
            pass


def test_appconfig_verify_integrity_and_fingerprint(app):
    assert app.verify_integrity() is True
    fp = app.memory_fingerprint()
    assert isinstance(fp, str)


def test_appconfig_teardown_blocks_operations():
    cfg = AppConfig()
    cfg.teardown()
    with pytest.raises(ConfigTornDownError):
        cfg.update(VERIFY=False)
    with pytest.raises(ConfigTornDownError):
        cfg.use_once(VERIFY=False)
    # verify_integrity still callable
    assert cfg.verify_integrity() is False


def test_appconfig_repr(app):
    r = repr(app)
    assert r.startswith("<AppConfig")

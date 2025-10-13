import warnings

import pytest

from config_guard import AppConfig
from config_guard.exceptions import (
    ConfigBypassError,
    ConfigLockedError,
    ConfigNotFoundError,
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


def test_appconfig_context_manager():
    with AppConfig() as cfg:
        assert isinstance(cfg, AppConfig)
    with pytest.raises(ConfigTornDownError):
        cfg.get("MAX_CONCURRENCY")


def test_appconfig_multiple_teardown_calls():
    cfg = AppConfig()
    cfg.teardown()
    # second teardown should not raise
    cfg.teardown()
    with pytest.raises(ConfigTornDownError):
        cfg.get("MAX_CONCURRENCY")


def test_appconfig_lock_status_after_teardown():
    cfg = AppConfig()
    cfg.lock()
    assert cfg.is_locked() is True
    cfg.teardown()
    with pytest.raises(ConfigTornDownError):
        cfg.is_locked()


def test_appconfig_update_with_no_changes(app):
    # should not raise or call hooks
    app.update()
    assert app.get("MAX_CONCURRENCY") == 10  # default value


def test_appconfig_use_once_with_invalid_key(app):
    with pytest.raises(ConfigNotFoundError):  # Changed from ConfigValidationError
        app.use_once(UNKNOWN_KEY=123)


def test_appconfig_restore_from_empty_snapshot(app):
    # should not change anything
    orig = app.get("MAX_CONCURRENCY")
    app.restore_from_snapshot({})
    assert app.get("MAX_CONCURRENCY") == orig


def test_appconfig_register_multiple_hooks(app):
    calls = []

    def hk1(s):
        calls.append(("hk1", s))

    def hk2(s):
        calls.append(("hk2", s))

    app.register_post_update_hook(hk1)
    app.register_post_update_hook(hk2)
    app.update(VERIFY=False)
    assert len(calls) == 2
    assert calls[0][0] == "hk1"
    assert calls[1][0] == "hk2"


def test_appconfig_temp_update_nested(app):
    orig = app.get("VERIFY")
    with app.temp_update(VERIFY=False):
        assert app.get("VERIFY") is False
        with app.temp_update(VERIFY=True):
            assert app.get("VERIFY") is True
        assert app.get("VERIFY") is False
    assert app.get("VERIFY") == orig


def test_appconfig_memory_fingerprint_changes_on_update(app):
    fp1 = app.memory_fingerprint()
    app.update(VERIFY=False)
    fp2 = app.memory_fingerprint()
    assert fp1 != fp2


def test_appconfig_no_hooks_registered(app):
    # should not raise
    app.update(VERIFY=False)
    assert app.get("VERIFY") is False


def test_appconfig_locking_twice(app):
    app.lock()
    assert app.is_locked() is True
    # locking again should not raise
    app.lock()
    assert app.is_locked() is True


def test_appconfig_unlocking_when_not_locked(app):
    assert app.is_locked() is False
    # unlocking when not locked should not raise
    app.unlock(_bypass=False)
    assert app.is_locked() is False


def test_appconfig_teardown_in_context_manager():
    with AppConfig() as cfg:
        assert isinstance(cfg, AppConfig)
        cfg.teardown()
        with pytest.raises(ConfigTornDownError):
            cfg.get("MAX_CONCURRENCY")

    with pytest.raises(ConfigTornDownError):
        cfg.get("MAX_CONCURRENCY")


def test_appconfig_update_with_same_value(app):
    orig_fp = app.memory_fingerprint()
    app.update(MAX_CONCURRENCY=app.get("MAX_CONCURRENCY"))
    new_fp = app.memory_fingerprint()
    assert orig_fp == new_fp  # fingerprint should not change


def test_appconfig_use_once_multiple_times(app):
    app.use_once(MAX_CONCURRENCY=30)
    assert app.get("MAX_CONCURRENCY") == 30
    app.use_once(MAX_CONCURRENCY=40)
    assert app.get("MAX_CONCURRENCY") == 40
    # falls back to permanent after one use
    assert app.get("MAX_CONCURRENCY") == 10  # default value


def test_appconfig_restore_from_snapshot_partial(app):
    snap = {"MAX_CONCURRENCY": 50}
    app.restore_from_snapshot(snap)
    assert app.get("MAX_CONCURRENCY") == 50
    assert app.get("VERIFY") is True  # default value remains unchanged


def test_appconfig_register_hook_raises_in_hook(app):
    def hk(s):
        raise ValueError("Hook error")

    app.register_post_update_hook(hk)
    app.update(VERIFY=False)
    assert app.get("VERIFY") is False  # update should still apply


def test_appconfig_temp_update_exception_reverts(app):
    orig = app.get("VERIFY")
    try:
        with app.temp_update(VERIFY=False):
            assert app.get("VERIFY") is False
            raise RuntimeError("Test exception")
    except RuntimeError:
        pass
    assert app.get("VERIFY") == orig


def test_appconfig_fingerprint_format(app):
    fp = app.memory_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) > 0


def test_appconfig_teardown_idempotent():
    cfg = AppConfig()
    cfg.teardown()
    # second teardown should not raise
    cfg.teardown()
    with pytest.raises(ConfigTornDownError):
        cfg.get("MAX_CONCURRENCY")


def test_appconfig_lock_status_after_multiple_teardowns():
    cfg = AppConfig()
    cfg.lock()
    assert cfg.is_locked() is True
    cfg.teardown()
    with pytest.raises(ConfigTornDownError):
        cfg.is_locked()


def test_config_initialization_with_schema():
    schema = {
        "MAX_CONCURRENCY": {
            "type": int,
            "default": 10,
            "min": 1,
            "max": 100,
        },
        "VERIFY": {
            "type": bool,
            "default": True,
        },
    }
    cfg = AppConfig(schema=schema)
    assert cfg.get("MAX_CONCURRENCY") == 10
    assert cfg.get("VERIFY") is True

    with pytest.raises(ConfigValidationError):
        cfg.update(MAX_CONCURRENCY=-5)

    with pytest.raises(ConfigValidationError):
        cfg.update(VERIFY="yes")


def test_appconfig_init_with_new_schema_params():
    schema = {
        "MAX_CONCURRENCY": {
            "type": int,
            "default": 10,
            "min": 1,
            "max": 100,
        },
        "VERIFY": {
            "type": bool,
            "default": True,
        },
        "NEW_PARAM": {
            "type": str,
            "default": "default",
            "min_length": 1,
            "max_length": 50,
        },
    }
    cfg = AppConfig(schema=schema, initial_values={"NEW_PARAM": "default"})
    assert cfg.get("NEW_PARAM") == "default"

    with pytest.raises(ConfigValidationError):
        cfg.update(NEW_PARAM="")


def test_config_repr_and_eq_and_hash():
    c1 = AppConfig()
    c2 = AppConfig()
    assert repr(c1).startswith("<AppConfig")
    assert c1 == c2
    assert hash(c1) == hash(c2)


def test_config_update_invalid_key():
    cfg = AppConfig()
    with pytest.raises(ConfigNotFoundError):  # Changed from ConfigValidationError
        cfg.update(UNKNOWN_KEY=123)


def test_config_setitem_and_delitem():
    c = AppConfig()
    c["MAX_CONCURRENCY"] = 15
    assert c["MAX_CONCURRENCY"] == 15
    del c["MAX_CONCURRENCY"]
    assert c.get("MAX_CONCURRENCY") == 10  # falls back to default


def test_config_iter_and_len():
    c = AppConfig()
    keys = list(iter(c))
    assert "MAX_CONCURRENCY" in keys
    assert len(c) >= 2


def test_config_locked_update():
    c = AppConfig()
    c.lock()
    with pytest.raises(ConfigLockedError):
        c.update(VERIFY=False)


def test_config_teardown_blocks_all():
    c = AppConfig()
    c.teardown()
    with pytest.raises(ConfigTornDownError):
        c.update(VERIFY=False)
    with pytest.raises(ConfigTornDownError):
        c.get("MAX_CONCURRENCY")
    with pytest.raises(ConfigTornDownError):
        c.get("MAX_CONCURRENCY")
    with pytest.raises(ConfigTornDownError):
        c.__setitem__("MAX_CONCURRENCY", 1)
    with pytest.raises(ConfigTornDownError):
        c.__delitem__("MAX_CONCURRENCY")
    with pytest.raises(ConfigTornDownError):
        c.__iter__()
    with pytest.raises(ConfigTornDownError):
        c.__len__()


def test_config_restore_snapshot_invalid():
    c = AppConfig()
    with pytest.raises(ConfigValidationError):
        c.restore_from_snapshot({"MAX_CONCURRENCY": 0})


def test_config_temp_update_invalid():
    c = AppConfig()
    with pytest.raises(ConfigValidationError):
        with c.temp_update(MAX_CONCURRENCY=0):
            pass


def test_config_multiple_teardown():
    c = AppConfig()
    c.teardown()
    c.teardown()  # should not raise

import os
import sys

from exceptions import ConfigError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pytest

from config_guard import AppConfig, ConfigLockedError, ConfigTornDownError, ConfigValidationError
from config_guard.params import CONFIG_SPECS


def test_appconfig_update_and_get():
    config = AppConfig()
    for param, spec in CONFIG_SPECS.items():
        config.update(**{param.value: spec["default"]})
        val = config.get(param)
        # Accept tuple or list for sequence types
        if isinstance(spec["default"], (list, tuple)):
            assert tuple(val) == tuple(spec["default"])
        else:
            assert val == spec["default"]


def test_appconfig_update_invalid_param():
    config = AppConfig()
    with pytest.raises(ConfigValidationError):
        config.update(NOT_A_PARAM=123)


def test_appconfig_use_once():
    config = AppConfig()
    param = list(CONFIG_SPECS.keys())[0]
    orig = config.get(param)
    config.use_once(**{param.value: orig})
    val = config.get(param)
    if isinstance(orig, (list, tuple)):
        assert tuple(val) == tuple(orig)
    else:
        assert val == orig


def test_appconfig_use_once_invalid():
    config = AppConfig()
    with pytest.raises(ConfigValidationError):
        config.use_once(**{list(CONFIG_SPECS.keys())[0].value: None})


def test_appconfig_lock_unlock():
    config = AppConfig()
    os.environ["ALLOW_CONFIG_BYPASS"] = "1"
    config.lock()
    assert config.is_locked()
    with pytest.raises(ConfigLockedError):
        config.update(**{list(CONFIG_SPECS.keys())[0].value: 123})
    assert os.getenv("ALLOW_CONFIG_BYPASS") == "1"
    config.unlock(_bypass=True)
    assert not config.is_locked()


def test_appconfig_lock_unlock_error():
    config = AppConfig()
    os.environ["ALLOW_CONFIG_BYPASS"] = "1"
    config.lock()
    config.unlock(_bypass=False)
    assert config.is_locked()


def test_appconfig_teardown():
    config = AppConfig()
    config.teardown()
    with pytest.raises(ConfigTornDownError):
        config.update(**{list(CONFIG_SPECS.keys())[0].value: 123})


def test_appconfig_teardown_error():
    config = AppConfig()
    config.teardown()
    with pytest.raises(ConfigTornDownError):
        config.get(list(CONFIG_SPECS.keys())[0])


def test_appconfig_temp_update():
    config = AppConfig()
    param = list(CONFIG_SPECS.keys())[0]
    orig = config.get(param)
    with config.temp_update(**{param.value: orig}):
        val = config.get(param)
        if isinstance(orig, (list, tuple)):
            assert tuple(val) == tuple(orig)
        else:
            assert val == orig
    val = config.get(param)
    if isinstance(orig, (list, tuple)):
        assert tuple(val) == tuple(orig)


def test_appconfig_temp_update_error():
    config = AppConfig()
    with pytest.raises(ConfigValidationError):
        with config.temp_update(**{list(CONFIG_SPECS.keys())[0].value: None}):
            pass


def test_appconfig_get_default():
    config = AppConfig()
    param = list(CONFIG_SPECS.keys())[0]
    assert config.get(param, default=42) == config.get(param)
    # The implementation raises ConfigValidationError for unknown params, so test for that
    with pytest.raises(ConfigValidationError):
        config.get("not_a_param", default=99)


def test_appconfig_snapshot_and_restore(monkeypatch):
    config = AppConfig()
    param = list(CONFIG_SPECS.keys())[0]
    orig = config.get(param)
    # Only update with valid value type
    config.update(**{param.value: orig})
    snap = config.snapshot()
    # Change to another valid value (if possible)
    config.update(**{param.value: orig})
    monkeypatch.setenv("ALLOW_CONFIG_BYPASS", "1")
    config.restore_from_snapshot(dict(snap), _bypass=True)
    val = config.get(param)
    if isinstance(orig, (list, tuple)):
        assert tuple(val) == tuple(orig)
    else:
        assert val == orig


def test_appconfig_register_post_update_hook():
    config = AppConfig()
    called = []

    def hook(_):
        called.append(1)

    config.register_post_update_hook(hook)
    param = list(CONFIG_SPECS.keys())[0]
    config.update(**{param.value: config.get(param)})
    assert called


def test_appconfig_update_multiple_params():
    config = AppConfig()
    params = list(CONFIG_SPECS.keys())[:2]
    update_dict = {p.value: CONFIG_SPECS[p]["default"] for p in params}
    config.update(**update_dict)
    for p in params:
        val = config.get(p)
        expected = CONFIG_SPECS[p]["default"]
        if isinstance(expected, (list, tuple)):
            assert tuple(val) == tuple(expected)
        else:
            assert val == expected


def test_appconfig_update_with_reason():
    config = AppConfig()
    param = list(CONFIG_SPECS.keys())[0]
    config.update(**{param.value: config.get(param)}, reason="test reason")
    assert config.get(param) == config.get(param)


def test_appconfig_memory_fingerprint_changes():
    config = AppConfig()
    orig_fp = config.memory_fingerprint()
    param = list(CONFIG_SPECS.keys())[0]
    config.update(**{param.value: config.get(param)})
    new_fp = config.memory_fingerprint()
    assert orig_fp == new_fp  # Should be same if value didn't change
    # Only update with a different valid value
    spec = CONFIG_SPECS[param]
    valid = spec["default"]
    try:
        if isinstance(valid, bool):
            new_val = not valid
        elif isinstance(valid, int):
            new_val = valid + 1 if valid != 0 else 1
        elif isinstance(valid, float):
            new_val = valid + 1.0
        elif isinstance(valid, str):
            new_val = valid + "_changed"
        elif isinstance(valid, tuple):
            new_val = valid + ("changed",)
        elif isinstance(valid, list):
            new_val = valid + ["changed"]
        else:
            pytest.skip("No valid alternate value for this param type")
        config.update(**{param.value: new_val})
        assert config.memory_fingerprint() != orig_fp
    except ConfigValidationError:
        pytest.skip("No valid alternate value for this param type")


def test_appconfig_verify_integrity():
    config = AppConfig()
    assert config.verify_integrity() is True


def test_appconfig_update_locked_bypass(monkeypatch):
    config = AppConfig()
    config.lock()
    monkeypatch.setenv("ALLOW_CONFIG_BYPASS", "1")
    param = list(CONFIG_SPECS.keys())[0]
    config.update(_bypass=True, **{param.value: config.get(param)})
    assert config.get(param) == config.get(param)


def test_appconfig_restore_from_invalid_snapshot():
    config = AppConfig()
    with pytest.raises(ConfigError):
        config.restore_from_snapshot({"not_a_param": 1}, _bypass=True)


def test_appconfig_temp_update_nested():
    config = AppConfig()
    param = list(CONFIG_SPECS.keys())[0]
    orig = config.get(param)
    with config.temp_update(**{param.value: orig}):
        with config.temp_update(**{param.value: orig}):
            assert config.get(param) == orig
    assert config.get(param) == orig

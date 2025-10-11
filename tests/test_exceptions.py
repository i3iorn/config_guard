import pytest

from config_guard.exceptions import (
    ConfigBypassError,
    ConfigLockedError,
    ConfigTornDownError,
    ConfigValidationError,
)


def test_config_validation_error():
    err = ConfigValidationError({"foo": "bad"}, "foo", 123)
    assert isinstance(err, Exception)
    assert "foo" in str(err)


def test_config_validation_error_empty():
    err = ConfigValidationError({}, None, None)
    assert isinstance(err, Exception)
    assert "Validation errors" in str(err)


def test_config_locked_error():
    with pytest.raises(ConfigLockedError):
        raise ConfigLockedError()


def test_config_locked_error_str():
    err = ConfigLockedError()
    assert isinstance(str(err), str)


def test_config_bypass_error():
    with pytest.raises(ConfigBypassError):
        raise ConfigBypassError()


def test_config_bypass_error_str():
    err = ConfigBypassError()
    assert isinstance(str(err), str)


def test_config_torn_down_error():
    with pytest.raises(ConfigTornDownError):
        raise ConfigTornDownError()


def test_config_torn_down_error_str():
    err = ConfigTornDownError()
    assert isinstance(str(err), str)

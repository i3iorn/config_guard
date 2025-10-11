from config_guard.exceptions import (
    ConfigBypassError,
    ConfigError,
    ConfigLockedError,
    ConfigTornDownError,
    ConfigValidationError,
)


def test_config_validation_error_message_and_attrs():
    err = ConfigValidationError({"FOO": "bad"}, key="FOO", value=123)
    assert "Validation errors" in str(err)
    assert err.errors == {"FOO": "bad"}
    assert err.key == "FOO"
    assert err.value == 123


def test_custom_exceptions_are_subclasses():
    assert issubclass(ConfigLockedError, ConfigError)
    assert issubclass(ConfigBypassError, ConfigError)
    assert issubclass(ConfigTornDownError, ConfigError)

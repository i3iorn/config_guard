import pytest

from config_guard.exceptions import ConfigValidationError
from config_guard.validation import ConfigValidator


def test_validator_validate_value_success_and_failures():
    v = ConfigValidator()

    # success
    v.validate_value("MAX_CONCURRENCY", 5)

    # key type wrong
    with pytest.raises(ConfigValidationError):
        v.validate_value(123, 5)  # type: ignore[arg-type]

    # unknown parameter
    with pytest.raises(ConfigValidationError):
        v.validate_value("UNKNOWN", 1)

    # wrong type
    with pytest.raises(ConfigValidationError):
        v.validate_value("VERIFY", 1)


def test_validator_validate_mapping_aggregates_errors():
    v = ConfigValidator()
    with pytest.raises(ConfigValidationError) as exc:
        v.validate_mapping({"MAX_CONCURRENCY": 0, "VERIFY": 2})
    # both should be present
    msg = str(exc.value)
    assert "MAX_CONCURRENCY" in msg and "VERIFY" in msg

from typing import Any

import pytest

from config_guard.exceptions import ConfigNotFoundError, ConfigValidationError
from config_guard.validation import ValidatorProtocol
from config_guard.validation.base import ConfigValidator


def test_validator_validate_value_success_and_failures():
    v = ConfigValidator()

    # success
    v.validate_value("MAX_CONCURRENCY", 5)

    # key type wrong
    with pytest.raises(ConfigValidationError):
        v.validate_value(123, 5)  # type: ignore[arg-type]

    # unknown parameter
    with pytest.raises(ConfigNotFoundError):
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


def test_validator_protocol():
    def sample_validator(value: int) -> None:
        if not isinstance(value, int) or value < 0:
            raise ConfigValidationError({"value": "Must be a non-negative integer."})

    # Ensure sample_validator conforms to ValidatorProtocol
    assert isinstance(sample_validator, ValidatorProtocol)

    # Test valid case
    sample_validator(10)

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        sample_validator(-5)

    with pytest.raises(ConfigValidationError):
        sample_validator("string")  # type: ignore[arg-type]


def test_validator_protocol_with_class():
    class SampleValidator:
        def __call__(self, value: int) -> None:
            if not isinstance(value, int) or value < 0:
                raise ConfigValidationError({"value": "Must be a non-negative integer."})

    validator_instance = SampleValidator()

    # Ensure instance conforms to ValidatorProtocol
    assert isinstance(validator_instance, ValidatorProtocol)

    # Test valid case
    validator_instance(10)

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        validator_instance(-5)

    with pytest.raises(ConfigValidationError):
        validator_instance("string")  # type: ignore[arg-type]


def test_validator_protocol_runtime_checkable():
    def another_validator(value: str) -> None:
        if not isinstance(value, str) or not value:
            raise ConfigValidationError({"value": "Must be a non-empty string."})

    # Ensure another_validator conforms to ValidatorProtocol
    assert isinstance(another_validator, ValidatorProtocol)

    # Test valid case
    another_validator("valid string")

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        another_validator("")  # Empty string

    with pytest.raises(ConfigValidationError):
        another_validator(123)  # type: ignore[arg-type]


def test_validator_protocol_with_lambda():
    def lambda_validator(value: float) -> None:
        if isinstance(value, float) and value >= 0.0:
            return
        else:
            raise ConfigValidationError({"value": "Must be a non-negative float."})

    # Ensure lambda_validator conforms to ValidatorProtocol
    assert isinstance(lambda_validator, ValidatorProtocol)

    # Test valid case
    lambda_validator(3.14)

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        lambda_validator(-1.0)

    with pytest.raises(ConfigValidationError):
        lambda_validator("string")  # type: ignore[arg-type]


def test_validator_protocol_with_complex_type():
    from typing import List

    def list_validator(value: List[int]) -> None:
        if not isinstance(value, list) or not all(isinstance(i, int) for i in value):
            raise ConfigValidationError({"value": "Must be a list of integers."})

    # Ensure list_validator conforms to ValidatorProtocol
    assert isinstance(list_validator, ValidatorProtocol)

    # Test valid case
    list_validator([1, 2, 3])

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        list_validator([1, "two", 3])  # type: ignore[list-item]

    with pytest.raises(ConfigValidationError):
        list_validator("not a list")  # type: ignore[arg-type]


def test_validator_protocol_with_noop():
    def noop_validator(value: Any) -> None:
        pass  # Always valid

    # Ensure noop_validator conforms to ValidatorProtocol
    assert isinstance(noop_validator, ValidatorProtocol)

    # Test with various types
    noop_validator(123)
    noop_validator("string")
    noop_validator([1, 2, 3])
    noop_validator({"key": "value"})
    noop_validator(None)


def test_validator_protocol_with_raises():
    def raises_validator(value: Any) -> None:
        raise ConfigValidationError({"value": "Always invalid."})

    # Ensure raises_validator conforms to ValidatorProtocol
    assert isinstance(raises_validator, ValidatorProtocol)

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        raises_validator(123)

    with pytest.raises(ConfigValidationError):
        raises_validator("string")

    with pytest.raises(ConfigValidationError):
        raises_validator([1, 2, 3])

    with pytest.raises(ConfigValidationError):
        raises_validator({"key": "value"})

    with pytest.raises(ConfigValidationError):
        raises_validator(None)


def test_validator_protocol_with_optional():
    from typing import Optional

    def optional_validator(value: Optional[int]) -> None:
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ConfigValidationError({"value": "Must be a non-negative integer or None."})

    # Ensure optional_validator conforms to ValidatorProtocol
    assert isinstance(optional_validator, ValidatorProtocol)

    # Test valid cases
    optional_validator(10)
    optional_validator(None)

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        optional_validator(-5)

    with pytest.raises(ConfigValidationError):
        optional_validator("string")  # type: ignore[arg-type]


def test_validator_protocol_with_union():
    from typing import Union

    def union_validator(value: Union[int, str]) -> None:
        if not isinstance(value, (int, str)):
            raise ConfigValidationError({"value": "Must be an integer or string."})

    # Ensure union_validator conforms to ValidatorProtocol
    assert isinstance(union_validator, ValidatorProtocol)

    # Test valid cases
    union_validator(10)
    union_validator("valid string")

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        union_validator(3.14)  # type: ignore[arg-type]

    with pytest.raises(ConfigValidationError):
        union_validator([])  # type: ignore[arg-type]


def test_validator_protocol_with_custom_exception():
    class CustomValidationError(ConfigValidationError):
        pass

    def custom_exception_validator(value: int) -> None:
        if not isinstance(value, int) or value < 0:
            raise CustomValidationError({"value": "Must be a non-negative integer."})

    # Ensure custom_exception_validator conforms to ValidatorProtocol
    assert isinstance(custom_exception_validator, ValidatorProtocol)

    # Test valid case
    custom_exception_validator(10)

    # Test invalid case
    with pytest.raises(CustomValidationError):
        custom_exception_validator(-5)

    with pytest.raises(CustomValidationError):
        custom_exception_validator("string")  # type: ignore[arg-type]


def test_validator_protocol_with_nested():
    from typing import Dict

    def nested_validator(value: Dict[str, int]) -> None:
        if not isinstance(value, dict) or not all(isinstance(v, int) for v in value.values()):
            raise ConfigValidationError({"value": "Must be a dict with integer values."})

    # Ensure nested_validator conforms to ValidatorProtocol
    assert isinstance(nested_validator, ValidatorProtocol)

    # Test valid case
    nested_validator({"a": 1, "b": 2})

    # Test invalid case
    with pytest.raises(ConfigValidationError):
        nested_validator({"a": 1, "b": "two"})  # type: ignore[dict-item]

    with pytest.raises(ConfigValidationError):
        nested_validator("not a dict")  # type: ignore[arg-type]

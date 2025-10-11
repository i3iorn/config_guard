import pytest

from config_guard.exceptions import ConfigValidationError
from config_guard.params import CONFIG_SPECS
from config_guard.validation import ConfigValidator


def test_validate_value_type():
    validator = ConfigValidator()
    for param, spec in CONFIG_SPECS.items():
        value = spec["default"]
        validator.validate_value(param, value)


def test_validate_value_type_error():
    validator = ConfigValidator()
    for param, spec in CONFIG_SPECS.items():
        # Only test wrong type if the default is not None and is a simple type
        if spec["type"] is str:
            wrong_type = 123
        elif spec["type"] is int:
            wrong_type = "bad"
        elif spec["type"] is list:
            wrong_type = 123
        else:
            continue
        if not isinstance(spec["default"], type(wrong_type)):
            with pytest.raises(ConfigValidationError):
                validator.validate_value(param, wrong_type)


def test_validate_mapping():
    validator = ConfigValidator()
    mapping = {param: spec["default"] for param, spec in CONFIG_SPECS.items()}
    validator.validate_mapping(mapping)
    mapping_bad = {param: None for param in CONFIG_SPECS}
    # Only test mapping_bad for params where None is not valid
    for param, spec in CONFIG_SPECS.items():
        if spec["default"] is not None:
            with pytest.raises(ConfigValidationError):
                validator.validate_value(param, None)

    with pytest.raises(ConfigValidationError):
        validator.validate_mapping(mapping_bad)

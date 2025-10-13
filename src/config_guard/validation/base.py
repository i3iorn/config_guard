from __future__ import annotations

from typing import Any, Dict

from config_guard.exceptions import ConfigValidationError
from config_guard.params import get_param_spec, resolve_param_name


class ConfigValidator:
    def validate_value(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise ConfigValidationError({str(key): "Key must be a str."})

        # Resolve through registry (raises ConfigValidationError if unknown)
        name = resolve_param_name(key)
        spec = get_param_spec(name)

        errors: Dict[str, str] = {}
        try:
            # Primary validation via ParamSpec (type, bounds, and custom validator)
            spec.validate(value)
        except ConfigValidationError as exc:
            errors.update(exc.errors)

        if errors:
            raise ConfigValidationError(errors, name, value)

    def validate_mapping(self, mapping: Dict[str, Any]) -> None:
        errors: Dict[str, str] = {}
        for k, v in mapping.items():
            try:
                self.validate_value(k, v)
            except ConfigValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ConfigValidationError(errors)

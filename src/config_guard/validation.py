from __future__ import annotations

import re
from typing import Any, Dict

from src.config_guard.exceptions import ConfigValidationError
from src.config_guard.params import CONFIG_SPECS, ConfigParam


class ConfigValidator:
    def __init__(self, specs: Dict[ConfigParam, Dict[str, Any]] | None = None):
        self._specs = specs or CONFIG_SPECS

    def validate_value(self, key: ConfigParam, value: Any) -> None:
        if not isinstance(key, ConfigParam):
            raise ConfigValidationError({str(key): "Key must be a ConfigParam."})

        if key not in self._specs:
            raise ConfigValidationError({key.value: "Unknown configuration parameter."})

        spec = self._specs.get(key)
        if spec is None:
            raise ConfigValidationError({key.value: "No spec defined."})

        errors: Dict[str, str] = {}
        exp_type = spec.get("type")
        if exp_type and not isinstance(value, exp_type):
            errors[key.value] = f"Expected {exp_type}, got {type(value)}"

        bounds = spec.get("bounds")
        if bounds and isinstance(value, (int, float)):
            lo, hi = bounds
            if not (lo <= value <= hi):
                errors[key.value] = f"Value {value} out of bounds [{lo},{hi}]"

        patt_re = spec.get("pattern")
        if patt_re and isinstance(value, str):
            if not re.match(patt_re, value):
                errors[key.value] = f"Pattern mismatch {patt_re}"

        cust = spec.get("validator")
        if cust and not cust(value):
            errors[key.value] = "Custom validator failed for "

        if errors:
            raise ConfigValidationError(errors, key, value)

    def validate_mapping(self, mapping: Dict[ConfigParam, Any]) -> None:
        errors: Dict[str, str] = {}
        for k, v in mapping.items():
            try:
                self.validate_value(k, v)
            except ConfigValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ConfigValidationError(errors)

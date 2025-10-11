from __future__ import annotations

import re
from typing import Any, Dict

from config_guard.exceptions import ConfigValidationError
from config_guard.params import get_param_spec, resolve_param_name


class ConfigValidator:
    def __init__(self, specs: Dict[str, Dict[str, Any]] | None = None):
        # Backward-compat arg retained but ignored; validation now consults the registry
        self._legacy_specs = specs or {}

    def validate_value(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise ConfigValidationError({str(key): "Key must be a str."})

        # Resolve through registry (raises ConfigValidationError if unknown)
        name = resolve_param_name(key)
        spec = get_param_spec(name)

        # If legacy specs were passed and contain additional constraints like pattern, honor them
        legacy = self._legacy_specs.get(name)

        errors: Dict[str, str] = {}
        try:
            # Primary validation via ParamSpec (type, bounds, and custom validator)
            spec.validate(value)
        except ConfigValidationError as exc:
            errors.update(exc.errors)

        # Optional legacy extras (pattern or stricter None semantics)
        if legacy:
            patt_re = legacy.get("pattern")
            if patt_re and isinstance(value, str):
                if not re.match(patt_re, value):
                    errors[name] = f"Pattern mismatch {patt_re}"

            # If a legacy spec has default not None and value is None, preserve stricter behavior
            if value is None and legacy.get("default") is not None:
                errors[name] = "None is not a valid value for this parameter."

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

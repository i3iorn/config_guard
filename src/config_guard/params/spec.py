from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from config_guard.exceptions import ConfigValidationError


@dataclass(frozen=True)
class ParamSpec:
    name: str
    default: Any
    value_type: Union[Type, Tuple[Type, ...]]
    validator: Optional[Callable[[Any], bool]] = None
    bounds: Optional[Tuple[Union[int, float], Union[int, float]]] = None
    description: Optional[str] = None
    allow_none: bool = True
    require_reason: bool = False

    def validate(self, value: Any) -> None:
        if value is None:
            if not self.allow_none:
                raise ConfigValidationError({self.name: "None value not allowed."})
            return

        try:
            if not isinstance(value, self.value_type):
                raise ConfigValidationError(
                    {self.name: f"Expected value_type {self.value_type}, got {type(value)}."}
                )
        except TypeError as e:
            raise ConfigValidationError(
                {self.name: f"Invalid value_type specification {self.value_type}."}
            ) from e

        if not self._bounds_check(value):
            assert self.bounds is not None
            lo, hi = self.bounds
            raise ConfigValidationError({self.name: f"Value {value} out of bounds [{lo}, {hi}]."})

        if self.validator is not None:
            try:
                valid = self.validator(value)
                if not valid:
                    raise ConfigValidationError({self.name: "Custom validator returned False."})
            except Exception as e:
                raise ConfigValidationError(
                    {self.name: f"Custom validator raised exception: {e}"}
                ) from e

        if not isinstance(self.require_reason, bool):
            raise ConfigValidationError({self.name: "require_reason must be a boolean value."})

    def _bounds_check(self, value: Any) -> bool:
        if self.has_bounds():
            assert self.bounds is not None
            lo, hi = self.bounds
            if isinstance(value, (str, list, tuple, dict)):
                return lo <= len(value) <= hi
            elif isinstance(value, (int, float)):
                return lo <= value <= hi
        return True

    def has_bounds(self) -> bool:
        return self.bounds is not None

    def to_mapping(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"default": self.default, "value_type": self.value_type}
        if self.validator is not None:
            d["validator"] = self.validator
        if self.bounds is not None:
            d["bounds"] = self.bounds
        if self.description:
            d["description"] = self.description
        return d

    def __getitem__(self, item: str) -> Any:
        return self.to_mapping()[item]

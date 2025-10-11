from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple, Union

from config_guard.exceptions import ConfigValidationError

logger = logging.getLogger("config_guard.params")
logger.addHandler(logging.NullHandler())

__all__ = [
    "ParamSpec",
    "ParamRegistry",
    "register_param",
    "get_param_spec",
    "list_params",
    "resolve_param_name",
    "get_all_specs",
    "REGISTRY",
    "dump_registry_state",
]


@dataclass(frozen=True)
class ParamSpec:
    name: str
    default: Any
    type: Union[type, Tuple[type, ...]]
    validator: Optional[Callable[[Any], bool]] = None
    bounds: Optional[Tuple[Union[int, float], Union[int, float]]] = None
    description: Optional[str] = None

    def validate(self, value: Any) -> None:
        if value is None and (
            self.type is type(None)
            or (isinstance(self.type, tuple) and any(t is type(None) for t in self.type))
        ):
            return
        if not isinstance(value, self.type):
            raise ConfigValidationError({self.name: f"Expected {self.type}, got {type(value)}."})
        if self.bounds is not None and isinstance(value, (int, float)):
            lo, hi = self.bounds
            if not (lo <= value <= hi):
                raise ConfigValidationError({self.name: f"Out of bounds [{lo}, {hi}]: {value}."})
        if self.validator is not None and not self.validator(value):
            raise ConfigValidationError({self.name: "Validation failed."})

    def to_mapping(self) -> dict:
        d = {"default": self.default, "type": self.type}
        if self.validator is not None:
            d["validator"] = self.validator
        if self.bounds is not None:
            d["bounds"] = self.bounds
        if self.description:
            d["description"] = self.description
        return d


class ParamRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, ParamSpec] = {}
        self._aliases: Dict[str, str] = {}
        logger.debug(
            "ParamRegistry initialized id=%s specs=%d aliases=%d",
            hex(id(self)),
            len(self._specs),
            len(self._aliases),
        )

    @staticmethod
    def _canon(name: str) -> str:
        return name.strip().upper()

    def register(
        self, spec: ParamSpec, aliases: Iterable[str] = (), override: bool = False
    ) -> None:
        key = self._canon(spec.name)
        logger.debug(
            "Register called: name=%r canon=%r override=%s aliases=%r",
            spec.name,
            key,
            override,
            tuple(aliases),
        )
        if not override and key in self._specs:
            logger.error("Register failed: %r already registered", key)
            raise ConfigValidationError({spec.name: "Parameter already registered."})
        existed = key in self._specs
        self._specs[key] = spec
        if existed and override:
            logger.debug("Spec overridden for %r", key)
        for a in aliases:
            ak = self._canon(a)
            if not override and ak in self._aliases and self._aliases[ak] != key:
                logger.error("Alias conflict: %r already points to %r", ak, self._aliases[ak])
                raise ConfigValidationError({a: f"Alias already used for {self._aliases[ak]}."})
            self._aliases[ak] = key
            logger.debug("Alias set: %r -> %r", ak, key)
        logger.debug(
            "Register complete: specs=%d aliases=%d keys(sample)=%r",
            len(self._specs),
            len(self._aliases),
            tuple(list(self._specs.keys())[:5]),
        )

    def has(self, name_or_alias: Union[str, Enum]) -> bool:
        try:
            resolved = self._resolve_key(name_or_alias)
            logger.debug("Has(%r) -> True (resolved=%r)", name_or_alias, resolved)
            return True
        except ConfigValidationError:
            logger.debug("Has(%r) -> False", name_or_alias)
            return False

    def get(self, name_or_alias: Union[str, Enum]) -> ParamSpec:
        key = self._resolve_key(name_or_alias)
        spec = self._specs[key]
        logger.debug("Get(%r) -> key=%r spec_id=%s", name_or_alias, key, hex(id(spec)))
        return spec

    def resolve_name(self, name_or_alias: Union[str, Enum]) -> str:
        key = self._resolve_key(name_or_alias)
        logger.debug("Resolve_name(%r) -> %r", name_or_alias, key)
        return key

    def _resolve_key(self, name_or_alias: Union[str, Enum]) -> str:
        # Detailed resolution logs
        logger.debug(
            "Resolving key for: %r (%s) | specs=%d aliases=%d",
            getattr(name_or_alias, "value", name_or_alias),
            type(name_or_alias),
            len(self._specs),
            len(self._aliases),
        )
        if _is_enum(name_or_alias):
            enum_val = getattr(name_or_alias, "value", None)
            if not isinstance(enum_val, str):
                logger.error("Enum value not a string: %r -> %r", name_or_alias, enum_val)
                raise ConfigValidationError({str(name_or_alias): "Enum value must be a string."})
            canon = self._canon(enum_val)
            in_specs = canon in self._specs
            in_aliases = canon in self._aliases
            logger.debug("Enum: canon=%r in_specs=%s in_aliases=%s", canon, in_specs, in_aliases)
            if in_specs:
                return canon
            if in_aliases:
                return self._aliases[canon]
        elif isinstance(name_or_alias, str):
            k = self._canon(name_or_alias)
            in_specs = k in self._specs
            in_aliases = k in self._aliases
            logger.debug("String: canon=%r in_specs=%s in_aliases=%s", k, in_specs, in_aliases)
            if in_specs:
                return k
            if in_aliases:
                return self._aliases[k]
        # Miss path
        all_keys_sample = tuple(list(self._specs.keys())[:10])
        alias_sample = tuple(list(self._aliases.items())[:10])
        key_str = str(getattr(name_or_alias, "value", name_or_alias))
        logger.error(
            "Unknown config param: %r | specs=%d aliases=%d | specs(sample)=%r aliases(sample)=%r",
            key_str,
            len(self._specs),
            len(self._aliases),
            all_keys_sample,
            alias_sample,
        )
        raise ConfigValidationError({str(self._canon(key_str)): "Unknown configuration parameter."})

    def all_names(self) -> Tuple[str, ...]:
        names = tuple(sorted(self._specs.keys()))
        logger.debug("All_names() -> %d keys", len(names))
        return names

    def clear(self) -> None:
        logger.debug("Clearing registry: specs=%d aliases=%d", len(self._specs), len(self._aliases))
        self._specs.clear()
        self._aliases.clear()
        logger.debug("Registry cleared.")


REGISTRY = ParamRegistry()


def register_param(
    name: str,
    *,
    default: Any,
    type,
    validator=None,
    bounds=None,
    description: str | None = None,
    aliases: Tuple[str, ...] = (),
    override: bool = False,
) -> None:
    REGISTRY.register(
        ParamSpec(
            name=name,
            default=default,
            type=type,
            validator=validator,
            bounds=bounds,
            description=description,
        ),
        aliases=aliases,
        override=override,
    )


def get_param_spec(key: "Enum | str") -> ParamSpec:
    return REGISTRY.get(key)


def resolve_param_name(key: "Enum | str") -> str:
    return REGISTRY.resolve_name(key)


def list_params() -> Tuple[str, ...]:
    return REGISTRY.all_names()


def get_all_specs() -> Mapping[str, dict]:
    return {name: REGISTRY.get(name).to_mapping() for name in REGISTRY.all_names()}


def dump_registry_state(max_items: int = 20) -> Dict[str, Any]:
    """
    Diagnostic helper to inspect current registry state for debugging purposes.
    Returns a dict with counts and samples of specs/aliases.
    """
    specs_keys = list(REGISTRY._specs.keys())  # type: ignore[attr-defined]
    aliases_items = list(REGISTRY._aliases.items())  # type: ignore[attr-defined]
    state = {
        "id": hex(id(REGISTRY)),
        "specs_count": len(specs_keys),
        "aliases_count": len(aliases_items),
        "specs_sample": tuple(specs_keys[:max_items]),
        "aliases_sample": tuple(aliases_items[:max_items]),
    }
    logger.debug("dump_registry_state -> %r", state)
    return state


def _is_enum(x: object) -> bool:
    try:
        return isinstance(x, Enum)
    except Exception:
        return False

from __future__ import annotations

import logging
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, Mapping, Optional, Tuple, Type, Union

from .registry import ParamRegistry
from .spec import ParamSpec

logger = logging.getLogger("config_guard.params")
logger.addHandler(logging.NullHandler())

__all__ = [
    "ParamSpec",
    "register_param",
    "get_param_spec",
    "list_params",
    "resolve_param_name",
    "get_all_specs",
    "dump_registry_state",
]

REGISTRY = ParamRegistry()


def register_param(
    name: str,
    *,
    default: Optional[Any] = None,
    value_type: Optional[Union[Type, Tuple[Type, ...]]] = None,
    validator: Optional[Callable[[Any], bool]] = None,
    bounds: Optional[Tuple[Union[int, float], Union[int, float]]] = None,
    description: str | None = None,
    aliases: Tuple[str, ...] = (),
    override: bool = False,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    min: Optional[Union[int, float]] = None,
    max: Optional[Union[int, float]] = None,
    require_reason: bool = False,
) -> None:
    if bounds is not None:
        if not (isinstance(bounds, tuple) and len(bounds) == 2):
            raise ValueError("bounds must be a tuple of (min, max)")
        if min is not None or max is not None:
            raise ValueError("Cannot specify both bounds and min/max")
        min, max = bounds
    if min_length is not None or max_length is not None:
        if value_type not in (str, list, tuple, dict):
            raise ValueError(
                "min_length/max_length can only be used with str, list, tuple, or dict types"
            )
        if bounds is not None:
            raise ValueError("Cannot specify both bounds and min_length/max_length")
        bounds = (min_length or 0, max_length or 0)
    if min is not None or max is not None:
        print(min, max)
        if value_type not in (int, float) and value_type != (int, float):
            raise ValueError("min/max can only be used with int or float types")
        if min is None or max is None:
            raise ValueError("Both min and max must be provided when using min/max")
        # keep numeric types as provided (int vs float)
        bounds = (min, max)
    if value_type is None:
        if default is not None:
            value_type = type(default)
        else:
            value_type = (str, int, float, bool, list, dict)

    REGISTRY.register(
        ParamSpec(
            name=name,
            default=default,
            value_type=value_type,
            validator=validator,
            bounds=bounds,
            description=description,
            require_reason=require_reason,
        ),
        aliases=aliases,
        override=override,
    )


def get_param_spec(key: "Enum | str") -> ParamSpec:
    """
    Return the ParamSpec for `key`.

    Optimization: if the caller provides a string that already looks like a canonical
    registry key (stripped, uppercased and present in the registry) bypass the
    full resolution path to avoid doing two lookups for the same parameter
    (common pattern: resolve_param_name(key) followed by get_param_spec(key)).
    """
    # Fast-path common case: canonical string already provided
    if isinstance(key, str):
        k = key.strip().upper()
        # Accessing the internal _specs dict here is a small, deliberate
        # micro-optimization to avoid calling REGISTRY._resolve_key again.
        try:
            return REGISTRY._specs[k]
        except KeyError:
            # fall back to the normal resolution path
            return REGISTRY.get(key)
    # Non-string (e.g. Enum) or other cases use the normal (safe) path
    return REGISTRY.get(key)


@lru_cache(maxsize=1024)
def resolve_param_name(key: "Enum | str") -> str:
    """Resolve an input (str or Enum) to the canonical registry key.

    This is cached for performance. The cache must be cleared when the
    registry mutates (see REGISTRY._clear_caches wiring below).
    """
    return REGISTRY.resolve_name(key)


def resolve_and_get(key: "Enum | str") -> tuple[str, ParamSpec]:
    """Resolve `key` and return tuple (canonical_name, ParamSpec).

    This is a single-call helper to avoid callers doing resolve + get
    (two dictionary lookups) in hot paths.
    """
    name = resolve_param_name(key)
    return name, get_param_spec(name)


def list_params() -> Tuple[str, ...]:
    return REGISTRY.all_names()


def get_all_specs() -> Mapping[str, Dict[str, Any]]:
    return {name: REGISTRY.get(name).to_mapping() for name in REGISTRY.all_names()}


def dump_registry_state(max_items: int = 20) -> Dict[str, Any]:
    """
    Diagnostic helper to inspect current registry state for debugging purposes.
    Returns a dict with counts and samples of specs/aliases.
    """
    specs_keys = list(REGISTRY._specs.keys())
    aliases_items = list(REGISTRY._aliases.items())
    state = {
        "id": hex(id(REGISTRY)),
        "specs_count": len(specs_keys),
        "aliases_count": len(aliases_items),
        "specs_sample": tuple(specs_keys[:max_items]),
        "aliases_sample": tuple(aliases_items[:max_items]),
    }
    logger.debug("dump_registry_state -> %r", state)
    return state


# Wire up cache clearing so registry operations can clear the resolve_name cache
# if/when the registry changes (new params / aliases). This is attached after
# the function is created to avoid circular import issues.
try:
    # resolve_param_name is decorated with lru_cache, so expose its cache_clear
    REGISTRY._clear_caches = resolve_param_name.cache_clear
except Exception:
    # No caching available or assignment failed; ignore silently
    REGISTRY._clear_caches = lambda: None

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Tuple, Type

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
    default: Any,
    type: Type,
    validator: Callable[[Any], bool] = None,
    bounds: Tuple[int, int] = None,
    description: str | None = None,
    aliases: Tuple[str, ...] = (),
    override: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    min: int | float | None = None,
    max: int | float | None = None,
) -> None:
    if bounds is not None:
        if not (isinstance(bounds, tuple) and len(bounds) == 2):
            raise ValueError("bounds must be a tuple of (min, max)")
        if min is not None or max is not None:
            raise ValueError("Cannot specify both bounds and min/max")
        min, max = bounds
    if min_length is not None or max_length is not None:
        if type not in (str, list, tuple, dict):
            raise ValueError(
                "min_length/max_length can only be used with str, list, tuple, or dict types"
            )
        if bounds is not None:
            raise ValueError("Cannot specify both bounds and min_length/max_length")
        bounds = (min_length, max_length)
    if min is not None or max is not None:
        if type not in (int, float):
            raise ValueError("min/max can only be used with int or float types")
        bounds = (min, max)

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

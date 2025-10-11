# src/config_guard/store.py
from __future__ import annotations

import logging
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict, Union

from config_guard.params import resolve_param_name
from config_guard.utils import _immutable_copy

logger = logging.getLogger("config_guard.store")
logger.addHandler(logging.NullHandler())


class ConfigStore:
    def __init__(self, mutable_types: bool = False) -> None:
        self._config: Dict[str, Any] = {}
        self._use_once: Dict[str, Any] = {}
        self._mutable_types = mutable_types
        logger.debug("ConfigStore init mutable_types=%s", self._mutable_types)

    def allows_mutable_types(self) -> bool:
        return self._mutable_types

    def set(self, key: str, value: Any, *, permanent: bool) -> None:
        tgt = self._config if permanent else self._use_once
        logger.debug(
            "Store.set key=%r permanent=%s incoming_type=%s current_type=%s",
            key,
            permanent,
            type(value),
            type(tgt.get(key)) if key in tgt else None,
        )
        # Always store an immutable copy; rely on _immutable_copy to freeze lists/dicts.
        imm_value = _immutable_copy(value)
        logger.debug(
            "Store.set after _immutable_copy key=%r imm_type=%s imm_value=%r",
            key,
            type(imm_value),
            imm_value,
        )
        # Optional guard: if mutable types are not allowed, ensure we didn't get a raw mutable type.
        if key in tgt and not self._mutable_types and not isinstance(imm_value, type(tgt[key])):
            logger.error(
                "Rejecting mutable type for key=%r original_type=%s imm_type=%s",
                key,
                type(value),
                type(imm_value),
            )
            raise ValueError(
                f"This configuration does not allow switching of types for key '{key}' "
                f"from {type(tgt[key])} to {type(imm_value)}."
            )
        tgt[key] = imm_value
        logger.debug("Store.set committed key=%r", key)

    def get(self, key: Union[str, str], default: Any = None) -> Any:
        key = resolve_param_name(key)

        if key in self._use_once:
            val = self._use_once.pop(key)
            return deepcopy(val)
        return deepcopy(self._config.get(key, default))

    def snapshot_internal(self) -> Dict[str, Any]:
        return {k: deepcopy(v) for k, v in self._config.items()}

    def snapshot_public(self) -> MappingProxyType:
        return MappingProxyType({k: deepcopy(v) for k, v in self._config.items()})

    def restore(self, values: Dict[str, Any]) -> None:
        self._config = {k: _immutable_copy(v) for k, v in values.items()}
        self._use_once.clear()

    def clear(self) -> None:
        self._config.clear()
        self._use_once.clear()

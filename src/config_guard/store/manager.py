from __future__ import annotations

import logging
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict, Union

from config_guard.params import get_param_spec, resolve_param_name
from config_guard.store.adaptors import PersistanceAdapterProtocol
from config_guard.utils import _immutable_copy

logger = logging.getLogger("config_guard.store")


class ConfigStore:
    def __init__(
        self, mutable_types: bool = False, persistance_adapter: PersistanceAdapterProtocol = None
    ) -> None:
        self._config: Dict[str, Any] = {}
        self._use_once: Dict[str, Any] = {}
        self._mutable_types = mutable_types
        self._persistance_adapter = persistance_adapter
        if self._persistance_adapter is not None:
            self.load()

        logger.debug("ConfigStore init mutable_types=%s", self._mutable_types)

    def allows_mutable_types(self) -> bool:
        return self._mutable_types

    def set(self, key: str, value: Any, *, permanent: bool) -> None:
        key = resolve_param_name(key)
        tgt = self._config if permanent else self._use_once
        imm_value = _immutable_copy(value)
        param_spec = get_param_spec(key)

        self._check_type(key, imm_value)
        self._check_bounds(param_spec, imm_value)
        param_spec.validate(imm_value)

        tgt[key] = imm_value

    def _check_type(self, key: str, value: Any) -> None:
        if key in self._config and not self._mutable_types:
            existing_type = type(self._config[key])
            param_spec = get_param_spec(key)
            new_type = type(value)

            if not isinstance(existing_type, tuple):
                existing_type = (existing_type,)

            if not isinstance(param_spec.type, tuple):
                param_spec_type = (param_spec.type,)
            else:
                param_spec_type = param_spec.type

            allowed_types = param_spec_type + existing_type

            if new_type not in allowed_types:
                logger.error(
                    "Attempted to change type of config key '%s' from %s to %s",
                    key,
                    existing_type,
                    new_type,
                )
                raise ValueError(
                    f"Cannot change type of config key '{key}' from {existing_type} to {new_type}"
                )

    def _check_bounds(self, param_spec, value):
        if param_spec is None or param_spec.bounds is None:
            return
        lo, hi = param_spec.bounds
        if isinstance(value, (int, float)) and not (lo <= value <= hi):
            logger.error(
                "Value %r for config key '%s' out of bounds [%s, %s]",
                value,
                param_spec.name,
                lo,
                hi,
            )
            raise ValueError(
                f"Value {value} for config key '{param_spec.name}' out of bounds [{lo}, {hi}]"
            )

    def get(self, key: Union[str, str], default: Any = None) -> Any:
        key = resolve_param_name(key)

        if key in self._use_once:
            val = self._use_once.pop(key)
            return deepcopy(val)
        return deepcopy(self._config.get(key, default))

    def load(self) -> None:
        if self._persistance_adapter is None:
            logger.error("Attempted to load config but no PersistanceAdapter is set")
            raise RuntimeError("No PersistanceAdapter set for loading configuration")
        try:
            loaded_config = self._persistance_adapter.load()
            if not isinstance(loaded_config, dict):
                logger.error("PersistanceAdapter.load() did not return a dict")
                raise ValueError("PersistanceAdapter.load() must return a dict")
            self._config = {k: _immutable_copy(v) for k, v in loaded_config.items()}
            self._use_once.clear()
            logger.debug("ConfigStore loaded config from persistance adapter: %r", self._config)
        except Exception as e:
            logger.error("Error loading config from persistance adapter: %s", e)
            raise

    def save(self) -> None:
        if self._persistance_adapter is None:
            logger.error("Attempted to save config but no PersistanceAdapter is set")
            raise RuntimeError("No PersistanceAdapter set for saving configuration")
        try:
            self._persistance_adapter.save(self.snapshot_internal())
            logger.debug("ConfigStore saved config to persistance adapter")
        except Exception as e:
            logger.error("Error saving config to persistance adapter: %s", e)
            raise

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

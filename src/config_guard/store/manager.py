from __future__ import annotations

import logging
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict, Optional, Tuple

from config_guard.history import History
from config_guard.params import get_param_spec, resolve_and_get, resolve_param_name
from config_guard.params.spec import ParamSpec
from config_guard.store.adaptors import PersistanceAdapterProtocol
from config_guard.utils import _immutable_copy

logger = logging.getLogger("config_guard.store")
logger.addHandler(logging.NullHandler())


class ConfigStore:
    def __init__(
        self,
        mutable_types: bool = False,
        persistance_adapter: Optional[PersistanceAdapterProtocol] = None,
        history: Optional[History] = None,
    ) -> None:
        self._config: Dict[str, Any] = {}
        self._use_once: Dict[str, Any] = {}
        self._mutable_types = mutable_types
        self._persistance_adapter = persistance_adapter
        self._history = history
        if self._persistance_adapter is not None:
            self.load()

        logger.debug("ConfigStore init mutable_types=%s", self._mutable_types)

    def allows_mutable_types(self) -> bool:
        return self._mutable_types

    def set(
        self,
        key: str,
        value: Any,
        *,
        permanent: bool,
        reason: str = "",
        modified_by: str = "unknown",
    ) -> None:
        # Resolve and fetch ParamSpec in one call to avoid double lookups
        name, param_spec = resolve_and_get(key)
        if param_spec.require_reason and not reason:
            logger.error("Setting config key '%s' requires a reason", name)
            raise ValueError(f"Setting config key '{name}' requires a reason")
        tgt = self._config if permanent else self._use_once
        imm_value = _immutable_copy(value)

        before_snapshot = {name: self._config.get(name)}

        self._check_type(name, imm_value, param_spec)

        self._check_bounds(param_spec, imm_value)
        param_spec.validate(imm_value)

        tgt[name] = imm_value

        # Record history if available
        try:
            if self._history is not None:
                self._history.add_entry(
                    modified_by=modified_by,
                    keys=[name],
                    reason=reason,
                    before=before_snapshot,
                    after={name: imm_value},
                )
        except Exception:
            # history is best-effort
            pass

    def _check_type(self, key: str, value: Any, param_spec: ParamSpec | None = None) -> None:
        if key in self._config and not self._mutable_types:
            existing_type_obj = type(self._config[key])
            if param_spec is None:
                param_spec = get_param_spec(key)
            new_type = type(value)

            existing_types: Tuple[type, ...] = (existing_type_obj,)

            if isinstance(param_spec.value_type, tuple):
                param_spec_types: Tuple[type, ...] = param_spec.value_type
            else:
                param_spec_types = (param_spec.value_type,)

            allowed_types: Tuple[type, ...] = param_spec_types + existing_types

            if new_type not in allowed_types:
                logger.error(
                    "Attempted to change value_type of config key '%s' from %s to %s",
                    key,
                    existing_types,
                    new_type,
                )
                raise ValueError(
                    f"Cannot change value_type of config key '{key}' from {existing_types} to {new_type}"
                )

    def _check_bounds(self, param_spec: ParamSpec, value: Any) -> None:
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

    def get(self, key: str, default: Any = None) -> Any:
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

    def snapshot_public(self) -> MappingProxyType[str, Any]:
        return MappingProxyType({k: deepcopy(v) for k, v in self._config.items()})

    def restore(
        self, values: Dict[str, Any], *, modified_by: str = "unknown", reason: str = "restore"
    ) -> None:
        before = dict(self._config)
        self._config = {k: _immutable_copy(v) for k, v in values.items()}
        self._use_once.clear()
        try:
            if self._history is not None:
                self._history.add_entry(
                    modified_by=modified_by,
                    keys=list(values.keys()),
                    reason=reason,
                    before=before,
                    after=dict(self._config),
                )
        except Exception:
            pass

    def clear(self, *, modified_by: str = "unknown") -> None:
        before = dict(self._config)
        self._config.clear()
        self._use_once.clear()
        try:
            if self._history is not None:
                self._history.add_entry(
                    modified_by=modified_by,
                    keys=[],
                    reason="clear",
                    before=before,
                    after={},
                )
        except Exception:
            pass

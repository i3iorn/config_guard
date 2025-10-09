# src/config_guard/store.py
from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict, Union
from src.config_guard.params import ConfigParam
from src.config_guard.utils import _immutable_copy


class ConfigStore:
    def __init__(self) -> None:
        self._config: Dict[ConfigParam, Any] = {}
        self._use_once: Dict[ConfigParam, Any] = {}

    def set(self, key: ConfigParam, value: Any, *, permanent: bool) -> None:
        tgt = self._config if permanent else self._use_once
        tgt[key] = _immutable_copy(value)

    def get(self, key: Union[ConfigParam, str], default: Any = None) -> Any:
        if isinstance(key, str):
            key = ConfigParam(key)
        if key in self._use_once:
            val = self._use_once.pop(key)
            return deepcopy(val)
        return deepcopy(self._config.get(key, default))

    def snapshot_internal(self) -> Dict[ConfigParam, Any]:
        return {k: deepcopy(v) for k, v in self._config.items()}

    def snapshot_public(self) -> MappingProxyType:
        return MappingProxyType({k.value: deepcopy(v) for k, v in self._config.items()})

    def restore(self, values: Dict[ConfigParam, Any]) -> None:
        self._config = {k: _immutable_copy(v) for k, v in values.items()}
        self._use_once.clear()

    def clear(self) -> None:
        self._config.clear()
        self._use_once.clear()

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from src.config_guard import ConfigParam


def _immutable_copy(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(deepcopy(value))
    if isinstance(value, dict):
        return MappingProxyType({k: deepcopy(v) for k, v in value.items()})
    return deepcopy(value)


def _stable_serialize_for_checksum(data: Dict[ConfigParam, Any]) -> bytes:
    out: Dict[str, Any] = {}
    for key in sorted(data.keys(), key=lambda k: k.value):
        val = data[key]
        try:
            json.dumps(val)
            out[key.value] = val
        except Exception:
            out[key.value] = repr(val)
    return json.dumps(out, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _checksum_of_config(snapshot: Dict[ConfigParam, Any], algorithm: str = "sha256") -> str:
    b = _stable_serialize_for_checksum(snapshot)
    return hashlib.new(algorithm, b).hexdigest()


def _require_bypass_env() -> bool:
    return os.getenv("ALLOW_CONFIG_BYPASS", "") == "1"

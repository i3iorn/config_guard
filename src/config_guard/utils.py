from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict

__all__ = [
    "_immutable_copy",
    "_stable_serialize_for_checksum",
    "_checksum_of_config",
    "_require_bypass_env",
]


def _immutable_copy(value: Any) -> Any:
    try:
        return _recursive_immutable_copy(value)
    except Exception as e:
        raise ValueError("Value is not deepcopy-able") from e


def _recursive_immutable_copy(value: Any) -> Any:
    try:
        if isinstance(value, list):
            return tuple(_recursive_immutable_copy(v) for v in value)
        if isinstance(value, dict):
            return MappingProxyType({k: _recursive_immutable_copy(v) for k, v in value.items()})
        return deepcopy(value)
    except Exception as e:
        raise ValueError("Value is not deepcopy-able") from e


def _stable_serialize_for_checksum(data: Dict[str, Any]) -> bytes:
    out: Dict[str, Any] = {}

    def safe_key_func(k: object) -> str:
        return repr(k)

    for og_key in sorted(data.keys(), key=safe_key_func):
        safe_key: str = safe_key_func(og_key)
        val = data[og_key]
        try:
            json.dumps(val)
            out[safe_key] = val
        except Exception:
            out[safe_key] = repr(val)
    return json.dumps(out, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _checksum_of_config(snapshot: Dict[str, Any], algorithm: str = "sha256") -> str:
    b = _stable_serialize_for_checksum(snapshot)
    return hashlib.new(algorithm, b).hexdigest()


def _require_bypass_env() -> bool:
    return os.getenv("ALLOW_CONFIG_BYPASS", "") == "1"

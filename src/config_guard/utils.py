from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict


def _immutable_copy(value: Any) -> Any:
    try:
        if isinstance(value, list):
            return tuple(deepcopy(value))
        if isinstance(value, dict):
            return MappingProxyType({k: deepcopy(v) for k, v in value.items()})
        return deepcopy(value)
    except Exception as e:
        raise ValueError("Value is not deepcopy-able") from e


def _stable_serialize_for_checksum(data: Dict[str, Any]) -> bytes:
    out: Dict[str, Any] = {}
    for key in sorted(data.keys(), key=lambda k: k):
        val = data[key]
        try:
            json.dumps(val)
            out[key] = val
        except Exception:
            out[key] = repr(val)
    return json.dumps(out, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _checksum_of_config(snapshot: Dict[str, Any], algorithm: str = "sha256") -> str:
    b = _stable_serialize_for_checksum(snapshot)
    return hashlib.new(algorithm, b).hexdigest()


def _require_bypass_env() -> bool:
    return os.getenv("ALLOW_CONFIG_BYPASS", "") == "1"

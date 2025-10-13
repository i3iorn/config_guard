"""
AppConfig: A robust, singleton configuration facade with validation, locking, integrity checks, and hooks.

- Enforces immutability and thread safety for configuration state.
- Supports validation, integrity, and lifecycle management.
- Designed for extensibility and safe runtime updates.
"""

from __future__ import annotations

from config_guard.config import AppConfig
from config_guard.exceptions import (
    ConfigBypassError,
    ConfigDuplicateError,
    ConfigLockedError,
    ConfigNotFoundError,
    ConfigTornDownError,
    ConfigValidationError,
)
from config_guard.params import (
    get_all_specs,
    get_param_spec,
    list_params,
    register_param,
    resolve_param_name,
)
from config_guard.validation import ValidatorProtocol

__all__ = [
    "AppConfig",
    "ConfigValidationError",
    "ConfigLockedError",
    "ConfigBypassError",
    "ConfigTornDownError",
    "register_param",
    "get_param_spec",
    "list_params",
    "resolve_param_name",
    "ValidatorProtocol",
    "get_all_specs",
    "ConfigNotFoundError",
    "ConfigDuplicateError",
]

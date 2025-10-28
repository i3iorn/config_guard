"""
AppConfig: A robust configuration facade with validation, locking, integrity checks, and hooks.

- Enforces immutability and thread safety for configuration state.
- Supports validation, integrity, and lifecycle management.
- Designed for extensibility and safe runtime updates.
- Provides clear error handling for configuration issues.
- Includes comprehensive documentation and usage examples.
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

# Singleton instance for module-level access, can be used directly as global config
Config = AppConfig()

__all__ = [
    "Config",
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

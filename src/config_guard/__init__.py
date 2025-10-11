"""
AppConfig: A robust, singleton configuration facade with validation, locking, integrity checks, and hooks.

- Enforces immutability and thread safety for configuration state.
- Supports validation, integrity, and lifecycle management.
- Designed for extensibility and safe runtime updates.
"""

from __future__ import annotations

import datetime
import inspect
import logging
import threading
import warnings
from contextlib import contextmanager
from types import MappingProxyType
from typing import Any, Dict, Iterator, Optional, Union

from config_guard.exceptions import (
    ConfigBypassError,
    ConfigLockedError,
    ConfigTornDownError,
    ConfigValidationError,
)
from config_guard.hooks import HookBus
from config_guard.integrity import IntegrityGuard
from config_guard.locks import LockGuard
from config_guard.params import (
    get_all_specs,
    get_param_spec,
    list_params,
    register_param,
    resolve_param_name,
)
from config_guard.store import ConfigStore
from config_guard.utils import _immutable_copy, _require_bypass_env
from config_guard.validation import ConfigValidator

logger = logging.getLogger("app_config_secure")
logger.addHandler(logging.NullHandler())


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
]


class AppConfig:
    """
    Singleton configuration manager with validation, locking, integrity, and hooks.

    Direct attribute assignment is forbidden; use update(), use_once(), or get().
    Use teardown() to clear state, and reset_singleton() for test environments.
    """

    SCHEMA_VERSION = 1
    HASH_ALGORITHM = "sha256"

    _global_lock = threading.RLock()

    def __init__(
        self,
        initial_values: Dict[str, Any] = None,
        schema: Optional[Dict[str, Any]] = None,
        *,
        allow_mutable_types: bool = False,
        immutable: bool = False,
    ) -> None:
        # internal lock for instance ops
        self.__lock = threading.RLock()

        # components
        self.__lock_guard = LockGuard()
        self.__validator = ConfigValidator()
        self.__store = ConfigStore(allow_mutable_types)
        self.__integrity = IntegrityGuard(self.HASH_ALGORITHM)
        self.__hooks = HookBus()

        # lifecycle/meta
        self.__torn_down = False
        self.__last_modified_by: Optional[str] = None
        self.__last_modified_at: Optional[datetime.datetime] = None
        self.__last_change_reason: Optional[str] = None

        if initial_values is None:
            initial_values = {}

        # init values
        bypass_startup = bool(initial_values.pop("_bypass", False))
        for param, spec in get_all_specs().items():
            val = _immutable_copy(initial_values.get(param, spec["default"]))
            if bypass_startup:
                if not _require_bypass_env():
                    raise ConfigBypassError("Startup bypass requires ALLOW_CONFIG_BYPASS=1")
                warnings.warn(f"Startup bypass for {param}={val!r}", UserWarning, stacklevel=2)
            else:
                self.__validator.validate_value(param, val)
            self.__store.set(param, val, permanent=True)

        # initial snapshot + checker
        self.__integrity.update_snapshot(self.__store.snapshot_internal())
        self.__integrity.start_checker(
            is_torn_down=lambda: self.__torn_down,
            on_violation=lambda msg: logger.critical(msg),
        )

        if immutable:
            self.lock()

    # forbid public attribute mutation
    def __setattr__(self, name, value):
        """
        Forbids direct public attribute assignment to ensure immutability.
        Use update(), use_once(), or get() for config access.
        """
        if hasattr(self, "_AppConfig__lock") and not name.startswith("_AppConfig__"):
            raise AttributeError("Direct attribute assignment forbidden. Use update()/use_once().")
        super().__setattr__(name, value)

    # locking
    def lock(self) -> None:
        """
        Lock the configuration, preventing further updates until unlocked.
        """
        with self.__lock:
            self.__lock_guard.lock()
            logger.info("AppConfig locked.")

    def unlock(self, _bypass: bool = False) -> None:
        """
        Unlock the configuration, allowing updates. Requires bypass if locked.
        """
        with self.__lock:
            self.__lock_guard.unlock(_bypass=_bypass)
            logger.warning("AppConfig unlocked.")

    def is_locked(self) -> bool:
        """
        Return True if the configuration is currently locked.
        """
        with self.__lock:
            return self.__lock_guard.is_locked()

    # updates
    def _caller_id(self) -> str:
        stack = inspect.stack()
        for frame in stack[2:]:
            module = frame.frame.f_globals.get("__name__")
            if module != __name__:
                return f"{module}:{frame.function}"
        return "unknown"

    def _apply_changes(self, changes: Dict[str, Any], *, permanent: bool, reason: str):
        for param, val in changes.items():
            self.__store.set(param, val, permanent=permanent)
        self.__last_modified_by = self._caller_id()
        self.__last_modified_at = datetime.datetime.now(tz=datetime.timezone.utc)
        self.__last_change_reason = reason
        self.__integrity.update_snapshot(self.__store.snapshot_internal())
        self.__hooks.run(self.__store.snapshot_internal())

    def _validate_and_resolve(
        self, input_dict: Dict[str, Any], *, bypass: bool = False, context: str = "update"
    ) -> Dict[str, Any]:
        """
        Helper to resolve and validate input values for config updates.
        Returns a dict of str to immutable value, or raises ConfigValidationError.
        Error messages include context and parameter name for clarity.
        """
        errors: Dict[str, str] = {}
        resolved: Dict[str, Any] = {}
        for k, v in input_dict.items():
            param = resolve_param_name(k)
            try:
                if not bypass:
                    self.__validator.validate_value(param, v)
                resolved[param] = _immutable_copy(v)
            except ConfigValidationError as exc:
                for err_key, err_msg in exc.errors.items():
                    errors[err_key] = f"[{context}] {err_msg}"
                logger.error(f"Validation error for {k} in {context}: {exc.errors}")
            except Exception as exc:
                errors[str(k)] = f"[{context}] {str(exc)}"
                logger.error(f"Error resolving {k} in {context}: {exc}")
        if errors:
            logger.error(f"{context} failed with errors: {errors}")
            raise ConfigValidationError(errors)
        return resolved

    def update(self, _bypass: bool = False, reason: str = "", **kwargs) -> None:
        """
        Update configuration parameters permanently. Validates input and logs errors.
        Logs info on success.
        """
        if self.__torn_down:
            logger.error("Attempted update after teardown.")
            raise ConfigTornDownError("Config has been torn down")
        with self.__lock:
            self.__lock_guard.ensure_unlocked(_bypass=_bypass)
            resolved_kwargs = self._validate_and_resolve(kwargs, bypass=_bypass, context="update")
            self._apply_changes(resolved_kwargs, permanent=True, reason=reason)
            logger.info(f"Config updated: {list(resolved_kwargs.keys())}")

    def use_once(self, _bypass: bool = False, reason: str = "", **kwargs) -> None:
        """
        Temporarily update configuration for the current session. Validates input and logs errors.
        Logs info on success.
        """
        if self.__torn_down:
            logger.error("Attempted use_once after teardown.")
            raise ConfigTornDownError("Config has been torn down")
        with self.__lock:
            self.__lock_guard.ensure_unlocked(_bypass=_bypass)
            resolved_kwargs = self._validate_and_resolve(kwargs, bypass=_bypass, context="use_once")
            self._apply_changes(resolved_kwargs, permanent=False, reason=reason)
            logger.info(f"Config temporarily updated: {list(resolved_kwargs.keys())}")

    def get(self, key: Union[str, str], default: Any = None) -> Any:
        """
        Get the value of a configuration parameter.
        """
        if self.__torn_down:
            logger.error("Attempted get after teardown.")
            raise ConfigTornDownError("Config has been torn down")
        key = resolve_param_name(key)
        with self.__lock:
            return self.__store.get(key, default)

    def snapshot(self) -> MappingProxyType:
        """
        Return a snapshot of the current configuration as a plain dictionary.
        """
        with self.__lock:
            return self.__store.snapshot_public()

    def restore_from_snapshot(self, snapshot: Dict[str, Any], _bypass: bool = False) -> None:
        """
        Restore configuration from a snapshot dictionary.
        Logs info on success.
        """
        if self.__torn_down:
            logger.error("Attempted restore_from_snapshot after teardown.")
            raise ConfigTornDownError("Config has been torn down")
        with self.__lock:
            self.__lock_guard.ensure_unlocked(_bypass=_bypass)
            resolved_kwargs = self._validate_and_resolve(
                snapshot, bypass=_bypass, context="restore_from_snapshot"
            )
            self.__store.restore(resolved_kwargs)
            self.__integrity.update_snapshot(self.__store.snapshot_internal())
            self.__hooks.run(self.__store.snapshot_internal())
            logger.info(f"Config restored from snapshot: {list(resolved_kwargs.keys())}")

    def register_post_update_hook(self, func) -> None:
        """
        Register a function to be called after each update.
        """
        with self.__lock:
            self.__hooks.register(func)

    @contextmanager
    def temp_update(self, _bypass: bool = False, **kwargs) -> Iterator[None]:
        """
        Context manager for temporary configuration changes. Restores state on exit.
        Logs exceptions raised within the context.
        Set _bypass=True to skip validation (for advanced/internal use).
        """
        with self.__lock:
            prior_config = self.__store.snapshot_internal()
            prior_checksum = self.__integrity.last_checksum
            try:
                resolved_kwargs = self._validate_and_resolve(
                    kwargs, bypass=_bypass, context="temp_update"
                )
                self._apply_changes(resolved_kwargs, permanent=True, reason="temp_update")
                logger.info(f"Temporary config update applied: {list(resolved_kwargs.keys())}")
                yield
            except Exception as exc:
                logger.error(f"Exception in temp_update context: {exc}")
                raise
            finally:
                self.__store.restore(prior_config)
                self.__integrity.update_snapshot(prior_config)
                if prior_checksum:
                    self.__integrity._last_checksum = prior_checksum
                logger.info("Temporary config update reverted.")

    def verify_integrity(self) -> bool:
        """
        Verify the integrity of the current configuration.
        """
        with self.__lock:
            return self.__integrity.verify()

    def memory_fingerprint(self) -> str:
        """
        Return a fingerprint of the current configuration state.
        """
        with self.__lock:
            return self.__integrity.memory_fingerprint()

    def teardown(self) -> None:
        """
        Tear down the configuration, clearing all state and hooks.
        """
        with self.__lock:
            self.__torn_down = True
            self.__store.clear()
            self.__hooks.clear()
            self.__integrity.clear()
            self.__last_modified_by = None
            self.__last_modified_at = None
            self.__last_change_reason = None

    def __repr__(self) -> str:
        """
        Return a string representation of the AppConfig instance.
        """
        with self.__lock:
            return f"<AppConfig locked={self.__lock_guard.is_locked()} checksum={self.__integrity.last_checksum}>"

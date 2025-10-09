from __future__ import annotations

import datetime
import inspect
import logging
import threading
import warnings
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Dict, Iterator, Optional, Union
from types import MappingProxyType

from src.config_guard.exceptions import (
    ConfigBypassError,
    ConfigLockedError,
    ConfigTornDownError,
    ConfigValidationError,
)
from src.config_guard.params import ConfigParam, CONFIG_SPECS
from src.config_guard.utils import _immutable_copy, _require_bypass_env
from src.config_guard.validation import ConfigValidator
from src.config_guard.store import ConfigStore
from src.config_guard.locks import LockGuard
from src.config_guard.integrity import IntegrityGuard
from src.config_guard.hooks import HookBus

logger = logging.getLogger("app_config_secure")
logger.addHandler(logging.NullHandler())


class AppConfig:
    SCHEMA_VERSION = 1
    HASH_ALGORITHM = "sha256"

    _instance: Optional["AppConfig"] = None
    _global_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._global_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._init_state(kwargs)
                cls._instance = inst
            return cls._instance

    def _init_state(self, initial_values: Dict[str, Any]):
        # internal lock for instance ops
        self.__lock = threading.Lock()

        # components
        self.__lock_guard = LockGuard()
        self.__validator = ConfigValidator(CONFIG_SPECS)
        self.__store = ConfigStore()
        self.__integrity = IntegrityGuard(self.HASH_ALGORITHM)
        self.__hooks = HookBus()

        # lifecycle/meta
        self.__torn_down = False
        self.__last_modified_by: Optional[str] = None
        self.__last_modified_at: Optional[datetime.datetime] = None
        self.__last_change_reason: Optional[str] = None

        # init values
        bypass_startup = bool(initial_values.pop("_bypass", False))
        for param, spec in CONFIG_SPECS.items():
            val = _immutable_copy(initial_values.get(param.value, spec["default"]))
            if bypass_startup:
                if not _require_bypass_env():
                    raise ConfigBypassError("Startup bypass requires ALLOW_CONFIG_BYPASS=1")
                warnings.warn(f"Startup bypass for {param.value}={val!r}", UserWarning)
            else:
                self.__validator.validate_value(param, val)
            self.__store.set(param, val, permanent=True)

        # initial snapshot + checker
        self.__integrity.update_snapshot(self.__store.snapshot_internal())
        self.__integrity.start_checker(
            is_torn_down=lambda: self.__torn_down,
            on_violation=lambda msg: logger.critical(msg),
        )

    # forbid public attribute mutation
    def __setattr__(self, name, value):
        if hasattr(self, "_AppConfig__lock") and not name.startswith("_AppConfig__"):
            raise AttributeError("Direct attribute assignment forbidden. Use update()/use_once().")
        super().__setattr__(name, value)

    # locking
    def lock(self):
        with self.__lock:
            self.__lock_guard.lock()
            logger.info("AppConfig locked.")

    def unlock(self, _bypass: bool = False):
        with self.__lock:
            self.__lock_guard.unlock(_bypass=_bypass)
            logger.warning("AppConfig unlocked.")

    def is_locked(self) -> bool:
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

    def _apply_changes(self, changes: Dict[ConfigParam, Any], *, permanent: bool, reason: str):
        for param, val in changes.items():
            self.__store.set(param, val, permanent=permanent)
        self.__last_modified_by = self._caller_id()
        self.__last_modified_at = datetime.datetime.utcnow()
        self.__last_change_reason = reason
        self.__integrity.update_snapshot(self.__store.snapshot_internal())
        self.__hooks.run(self.__store.snapshot_internal())


    def update(self, _bypass: bool = False, reason: str = "", **kwargs):
        if self.__torn_down:
            raise ConfigTornDownError("Config has been torn down")
        with self.__lock:
            self.__lock_guard.ensure_unlocked(_bypass=_bypass)

            resolved_kwargs = {
                self.__resolve_param(k, errors={}): v for k, v in kwargs.items()
            }

            self.__validate_input_dictionary(resolved_kwargs)

            converted: Dict[ConfigParam, Any] = {
                param: _immutable_copy(v) for param, v in resolved_kwargs.items()
            }

            self._apply_changes(converted, permanent=True, reason=reason)

    def __resolve_param(self, key: Union[ConfigParam, str], errors: Dict[str, str] = None) -> ConfigParam:
        if isinstance(key, ConfigParam):
            return key
        try:
            return ConfigParam(key.upper())
        except ValueError:
            if errors is not None:
                errors[key] = "Unknown parameter"
                return None
            else:
                raise ConfigValidationError({key: "Unknown parameter"})

    def __validate_input_dictionary(self, input_dict: Dict[ConfigParam, Any]) -> None:
        errors: Dict[str, str] = {}
        for k, v in input_dict.items():
            val = _immutable_copy(v)
            try:
                self.__validator.validate_value(k, val)
            except ConfigValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ConfigValidationError(errors)

    def use_once(self, _bypass: bool = False, reason: str = "", **kwargs):
        if self.__torn_down:
            raise ConfigTornDownError("Config has been torn down")
        with self.__lock:
            self.__lock_guard.ensure_unlocked(_bypass=_bypass)
            converted: Dict[ConfigParam, Any] = {}
            errors: Dict[str, str] = {}
            for k, v in kwargs.items():
                param = self.__resolve_param(k, errors)
                if param:
                    val = _immutable_copy(v)
                    if not _bypass:
                        try:
                            self.__validator.validate_value(param, val)
                        except ConfigValidationError as exc:
                            errors.update(exc.errors)
                    converted[param] = val
            if errors:
                raise ConfigValidationError(errors)
            self._apply_changes(converted, permanent=False, reason=reason)

    def get(self, key: Union[ConfigParam, str], default: Any = None) -> Any:
        if self.__torn_down:
            raise ConfigTornDownError("Config has been torn down")

        key = self.__resolve_param(key)

        with self.__lock:
            return self.__store.get(key, default)

    def snapshot(self) -> MappingProxyType:
        with self.__lock:
            return self.__store.snapshot_public()

    def restore_from_snapshot(self, snapshot: Dict[str, Any], _bypass: bool = False):
        if self.__torn_down:
            raise ConfigTornDownError("Config has been torn down")
        with self.__lock:
            self.__lock_guard.ensure_unlocked(_bypass=_bypass)

            resolved_kwargs = {
                self.__resolve_param(k, errors={}): v for k, v in snapshot.items()
            }
            self.__validate_input_dictionary(resolved_kwargs)
            converted: Dict[ConfigParam, Any] = {
                param: _immutable_copy(v) for param, v in resolved_kwargs.items()
            }

            self.__store.restore(converted)
            self.__integrity.update_snapshot(self.__store.snapshot_internal())
            self.__hooks.run(self.__store.snapshot_internal())

    # hooks
    def register_post_update_hook(self, func):
        with self.__lock:
            self.__hooks.register(func)

    # context manager
    @contextmanager
    def temp_update(self, **kwargs) -> Iterator[None]:
        with self.__lock:
            prior_config = self.__store.snapshot_internal()
            prior_checksum = self.__integrity.last_checksum
            try:
                self.update(**kwargs)
                yield
            finally:
                self.__store.restore(prior_config)
                # restore integrity snapshot/checksum
                self.__integrity.update_snapshot(prior_config)
                # overwrite checksum to original sealed value if present
                # note: update_snapshot recomputes; if you need exact previous sealed value, track separately
                if prior_checksum:
                    # recompute then set back to prior to avoid false positives
                    self.__integrity._last_checksum = prior_checksum  # internal, acceptable here

    # integrity
    def verify_integrity(self) -> bool:
        with self.__lock:
            return self.__integrity.verify()

    def memory_fingerprint(self) -> str:
        with self.__lock:
            return self.__integrity.memory_fingerprint()

    # teardown
    def teardown(self):
        with self.__lock:
            self.__torn_down = True
            self.__store.clear()
            self.__hooks.clear()
            self.__integrity.clear()
            self.__last_modified_by = None
            self.__last_modified_at = None
            self.__last_change_reason = None

    # repr
    def __repr__(self):
        with self.__lock:
            return f"<AppConfig locked={self.__lock_guard.is_locked()} checksum={self.__integrity.last_checksum}>"

from __future__ import annotations

from src.config_guard.exceptions import ConfigBypassError, ConfigLockedError
from src.config_guard.utils import _require_bypass_env


class LockGuard:
    def __init__(self) -> None:
        self._locked = False

    def lock(self) -> None:
        self._locked = True

    def unlock(self, *, _bypass: bool = False) -> None:
        if _bypass and not _require_bypass_env():
            raise ConfigBypassError("Unlock bypass requires ALLOW_CONFIG_BYPASS=1")
        self._locked = False

    def ensure_unlocked(self, *, _bypass: bool) -> None:
        if self._locked and not _bypass:
            raise ConfigLockedError()
        if _bypass and not _require_bypass_env():
            raise ConfigBypassError()

    def is_locked(self) -> bool:
        return self._locked

from __future__ import annotations

import warnings

from .exceptions import ConfigBypassError, ConfigLockedError
from .utils import _require_bypass_env


class LockGuard:
    def __init__(self) -> None:
        self._locked = False

    def lock(self) -> None:
        self._locked = True

    def unlock(self, *, _bypass: bool = False) -> None:
        if _bypass and _require_bypass_env():
            self._locked = False
        elif _bypass and not _require_bypass_env():
            raise ConfigBypassError()
        elif not self._locked:
            pass  # Already unlocked
        elif not _bypass and self._locked:
            warnings.warn(
                "Config is still locked. Unlock requires ALLOW_CONFIG_BYPASS=1 and _bypass=True",
                UserWarning,
                stacklevel=2,
            )
        else:
            raise RuntimeError("Unreachable state in unlock")

    def ensure_unlocked(self, *, _bypass: bool) -> None:
        if self._locked and not _bypass:
            raise ConfigLockedError()
        if _bypass and not _require_bypass_env():
            raise ConfigBypassError()

    def is_locked(self) -> bool:
        return self._locked

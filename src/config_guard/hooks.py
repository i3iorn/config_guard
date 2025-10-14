from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Literal

logger = logging.getLogger("config_guard.hooks")
logger.addHandler(logging.NullHandler())

Hook = Callable[[Dict[str, Any]], None]


class HookBus:
    def __init__(self, failure_mode: Literal["ignore", "log", "raise"] = "ignore") -> None:
        self._hooks: List[Hook] = []

        if failure_mode not in ("ignore", "log", "raise"):
            raise ValueError("failure_mode must be one of 'ignore', 'log', 'raise'")
        self._failure_mode = failure_mode

    def register(self, func: Hook) -> None:
        if not callable(func):
            raise TypeError("Hook must be callable")
        self._hooks.append(func)

    def run(self, config_snapshot: Dict[str, Any]) -> None:
        for hook in self._hooks:
            try:
                hook(config_snapshot)
            except Exception as exc:
                if self._failure_mode == "raise":
                    raise
                elif self._failure_mode == "log":
                    logger.error("Hook %r failed: %s", hook, exc)
                else:
                    # If set to ignore we still log at debug level
                    logger.debug("Hook %r failed but ignored: %s", hook, exc)

    def clear(self) -> None:
        self._hooks.clear()

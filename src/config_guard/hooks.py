from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Literal

from config_guard.params import ConfigParam

logger = logging.getLogger("app_config_secure")
logger.addHandler(logging.NullHandler())


class HookBus:
    def __init__(self, failure_mode: Literal["ignore", "log", "raise"] = "ignore") -> None:
        self._hooks: List[Callable[[Dict[ConfigParam, Any]], None]] = []

        if failure_mode not in ("ignore", "log", "raise"):
            raise ValueError("failure_mode must be one of 'ignore', 'log', 'raise'")
        self._failure_mode = failure_mode

    def register(self, func: Callable[[Dict[ConfigParam, Any]], None]) -> None:
        if not callable(func):
            raise TypeError("Hook must be callable")
        self._hooks.append(func)

    def run(self, config_snapshot: Dict[ConfigParam, Any]) -> None:
        for hook in self._hooks:
            try:
                hook(config_snapshot)
            except Exception as exc:
                if self._failure_mode == "raise":
                    raise
                elif self._failure_mode == "log":
                    logger.error(f"Hook {hook} failed: {exc}")
                else:
                    # If set to ignore we still log at debug level
                    logger.debug(f"Hook {hook} failed but ignored: {exc}")

    def clear(self) -> None:
        self._hooks.clear()

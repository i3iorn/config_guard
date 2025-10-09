# src/config_guard/hooks.py
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List
from src.config_guard.params import ConfigParam

logger = logging.getLogger("app_config_secure")
logger.addHandler(logging.NullHandler())


class HookBus:
    def __init__(self) -> None:
        self._hooks: List[Callable[[Dict[ConfigParam, Any]], None]] = []

    def register(self, func: Callable[[Dict[ConfigParam, Any]], None]) -> None:
        self._hooks.append(func)

    def run(self, config_snapshot: Dict[ConfigParam, Any]) -> None:
        for hook in self._hooks:
            try:
                hook(config_snapshot)
            except Exception as exc:
                logger.exception("Post-update hook raised exception: %s", exc)

    def clear(self) -> None:
        self._hooks.clear()

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from config_guard.utils import _checksum_of_config


class IntegrityGuard:
    def __init__(self, hash_algorithm: str = "sha256") -> None:
        if not hasattr(hashlib, hash_algorithm):
            raise ValueError(f"Unknown hash algorithm: {hash_algorithm}")
        self._algo = hash_algorithm
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._last_checksum: Optional[str] = None
        self._checker_thread: Optional[threading.Thread] = None

    @property
    def last_checksum(self) -> Optional[str]:
        return self._last_checksum

    def seal_checksum(self, checksum: str) -> str:
        """
        Optionally seal the checksum with HMAC using a key from the environment.
        If no key is set, returns the checksum unchanged.
        If a key is set, returns the HMAC of the checksum.
        Raises if HMAC computation fails.

        Raises:
        - ValueError: If the HMAC computation fails due to an invalid algorithm.
        - TypeError: If the key or checksum are of invalid types.
        - Exception: For any other exceptions raised during HMAC computation.
        """
        key = os.getenv("CONFIG_HMAC_KEY", "")
        if not key:
            return checksum
        # Use algorithm name directly as digestmod to satisfy hmac.new contract
        return hmac.new(key.encode(), checksum.encode(), self._algo).hexdigest()

    def update_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self._last_snapshot = {k: deepcopy(v) for k, v in snapshot.items()}
        raw = _checksum_of_config(self._last_snapshot, self._algo)
        self._last_checksum = self.seal_checksum(raw)

    def verify(self) -> bool:
        if not self._last_snapshot or not self._last_checksum:
            return False
        raw = _checksum_of_config(self._last_snapshot, self._algo)
        sealed = self.seal_checksum(raw)
        return sealed == self._last_checksum

    def start_checker(
        self, *, is_torn_down: Callable[[], bool], on_violation: Callable[[str], None]
    ) -> None:
        def _loop():
            evt = threading.Event()
            while not is_torn_down():
                if not self.verify():
                    on_violation("AppConfig integrity violation detected")
                evt.wait(10)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        self._checker_thread = t

    def memory_fingerprint(self) -> str:
        data = {
            "pid": os.getpid(),
            "checksum": self._last_checksum,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def join(self) -> None:
        if self._checker_thread:
            self._checker_thread.join()

    def clear(self) -> None:
        self._last_snapshot = None
        self._last_checksum = None

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class HistoryEntry:
    timestamp: datetime.datetime
    modified_by: str
    reason: str
    keys: List[str]
    before: Dict[str, Any]
    after: Dict[str, Any]


class History:
    """Thread-safe in-memory audit trail for configuration changes.

    This is intentionally simple: entries are appended in memory. The class
    provides methods to add an entry, list entries, and clear the history.
    A production system could swap this for a persistence-backed adaptor.
    """

    def __init__(self, max_entries: Optional[int] = None) -> None:
        self._lock = threading.RLock()
        self._entries: List[HistoryEntry] = []
        self._max_entries = max_entries

    def add_entry(
        self,
        modified_by: str,
        keys: List[str],
        reason: str,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> None:
        entry = HistoryEntry(
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
            modified_by=modified_by,
            reason=reason or "",
            keys=list(keys),
            before=dict(before),
            after=dict(after),
        )
        with self._lock:
            self._entries.append(entry)
            if self._max_entries is not None and len(self._entries) > self._max_entries:
                # drop oldest
                del self._entries[0 : len(self._entries) - self._max_entries]

    def all_entries(self) -> List[HistoryEntry]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

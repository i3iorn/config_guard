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
    provides methods to add an entry, list entries, clear the history, and
    exposes convenient accessors for the most recent change metadata.
    """

    def __init__(self, max_entries: Optional[int] = None) -> None:
        self._lock = threading.RLock()
        self._entries: List[HistoryEntry] = []
        self._max_entries = max_entries
        # last-change metadata (kept in lock)
        self._last_modified_by: Optional[str] = None
        self._last_modified_at: Optional[datetime.datetime] = None
        self._last_change_reason: Optional[str] = None
        self._last_modified_parameters: Optional[List[str]] = None

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
            # update last-change metadata
            self._last_modified_by = modified_by
            self._last_modified_at = entry.timestamp
            self._last_change_reason = reason or ""
            self._last_modified_parameters = list(keys)
            if self._max_entries is not None and len(self._entries) > self._max_entries:
                # drop oldest
                del self._entries[0 : len(self._entries) - self._max_entries]

    def all_entries(self) -> List[HistoryEntry]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._last_modified_by = None
            self._last_modified_at = None
            self._last_change_reason = None
            self._last_modified_parameters = None

    # convenience accessors for last-change metadata
    @property
    def last_modified_by(self) -> Optional[str]:
        with self._lock:
            return self._last_modified_by

    @property
    def last_modified_at(self) -> Optional[datetime.datetime]:
        with self._lock:
            return self._last_modified_at

    @property
    def last_change_reason(self) -> Optional[str]:
        with self._lock:
            return self._last_change_reason

    @property
    def last_modified_parameters(self) -> Optional[List[str]]:
        with self._lock:
            return (
                None
                if self._last_modified_parameters is None
                else list(self._last_modified_parameters)
            )

    @property
    def last_change(self) -> Dict[str, str]:
        """Return a small summary dict describing the most recent change."""
        with self._lock:
            return {
                "modified_by": self._last_modified_by or "",
                "modified_at": self._last_modified_at.isoformat() if self._last_modified_at else "",
                "change_reason": self._last_change_reason or "",
                "modified_parameters": (
                    ", ".join(self._last_modified_parameters)
                    if self._last_modified_parameters
                    else ""
                ),
            }

    def formatted_entries(self) -> List[Dict[str, Any]]:
        """Return a list of entries as plain dicts with ISO timestamps.

        This keeps formatting logic inside History so callers (like AppConfig)
        don't need to repeat it.
        """
        with self._lock:
            out: List[Dict[str, Any]] = []
            for e in self._entries:
                out.append(
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "modified_by": e.modified_by,
                        "reason": e.reason,
                        "keys": list(e.keys),
                        "before": dict(e.before),
                        "after": dict(e.after),
                    }
                )
            return out

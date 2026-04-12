"""Stale context eviction rules (Playbook §9.4)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple


class ContextEviction:
    """Evict stale context entries based on TTL and LRU."""

    def __init__(self, ttl_seconds: float = 300.0, max_entries: int = 100) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: Dict[str, Tuple[Any, float, int]] = {}
        self._access_counter = 0

    def put(self, key: str, value: Any) -> None:
        self._access_counter += 1
        self._entries[key] = (value, time.monotonic(), self._access_counter)
        self._evict_if_needed()

    def get(self, key: str) -> Optional[Any]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        value, ts, _ = entry
        if time.monotonic() - ts > self.ttl_seconds:
            del self._entries[key]
            return None
        self._access_counter += 1
        self._entries[key] = (value, ts, self._access_counter)
        return value

    def evict_stale(self) -> int:
        now = time.monotonic()
        stale = [k for k, (_, ts, _) in self._entries.items() if now - ts > self.ttl_seconds]
        for k in stale:
            del self._entries[k]
        return len(stale)

    def _evict_if_needed(self) -> None:
        if len(self._entries) > self.max_entries:
            self.evict_stale()
        if len(self._entries) > self.max_entries:
            sorted_entries = sorted(
                self._entries.items(), key=lambda x: x[1][2]
            )
            to_remove = len(self._entries) - self.max_entries
            for k, _ in sorted_entries[:to_remove]:
                del self._entries[k]

    @property
    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

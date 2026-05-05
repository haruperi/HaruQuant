"""Hot snapshot caching with freshness metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from services.utils.logger import logger
from services.utils import Clock, FreshnessWindow, SystemClock
from services.utils.time_utils import evaluate_freshness


SnapshotT = TypeVar("SnapshotT")


@dataclass(frozen=True)
class SnapshotCacheEntry(Generic[SnapshotT]):
    key: str
    snapshot: SnapshotT
    observed_at: object
    max_age_seconds: int

    def freshness(self, *, clock: Clock | None = None) -> FreshnessWindow:
        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=clock,
        )


class HotSnapshotCache(Generic[SnapshotT]):
    """Small in-memory stand-in for a Redis-backed hot snapshot cache."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._entries: dict[str, SnapshotCacheEntry[SnapshotT]] = {}

    def put(self, entry: SnapshotCacheEntry[SnapshotT]) -> SnapshotCacheEntry[SnapshotT]:
        self._entries[entry.key] = entry
        return entry

    def get(self, key: str) -> SnapshotCacheEntry[SnapshotT] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.freshness(clock=self._clock).is_stale:
            self._entries.pop(key, None)
            return None
        return entry

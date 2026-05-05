from __future__ import annotations

from datetime import datetime, timezone

from haruquant.utils import FixedClock
from haruquant.execution import HotSnapshotCache, SnapshotCacheEntry


def test_hot_snapshot_cache_returns_only_fresh_entries() -> None:
    cache = HotSnapshotCache(
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 3, tzinfo=timezone.utc))
    )
    cache.put(
        SnapshotCacheEntry(
            key="mkt:EURUSD",
            snapshot={"symbol": "EURUSD"},
            observed_at=datetime(2026, 4, 9, 10, 0, 0, tzinfo=timezone.utc),
            max_age_seconds=5,
        )
    )
    cache.put(
        SnapshotCacheEntry(
            key="mkt:GBPUSD",
            snapshot={"symbol": "GBPUSD"},
            observed_at=datetime(2026, 4, 9, 10, 0, 0, tzinfo=timezone.utc),
            max_age_seconds=2,
        )
    )

    assert cache.get("mkt:EURUSD") is not None
    assert cache.get("mkt:GBPUSD") is None

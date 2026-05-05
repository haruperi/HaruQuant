from __future__ import annotations

from datetime import datetime, timezone

import pytest

from data.database import resolve_partition_target


def test_resolve_partition_target_routes_high_volume_tables_by_month() -> None:
    target = resolve_partition_target(
        base_table="audit_trajectory_logs",
        event_time=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )

    assert target.base_table == "audit_trajectory_logs"
    assert target.partition_table == "audit_trajectory_logs__p2026_04"


def test_resolve_partition_target_rejects_unconfigured_tables() -> None:
    with pytest.raises(ValueError, match="not configured"):
        resolve_partition_target(
            base_table="gov_policies",
            event_time=datetime(2026, 4, 9, tzinfo=timezone.utc),
        )

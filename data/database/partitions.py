"""Logical partition routing for high-volume event tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_PARTITIONED_TABLES = frozenset(
    {
        "core_workflow_transitions",
        "core_observations",
        "audit_trajectory_logs",
    }
)


@dataclass(frozen=True)
class PartitionTarget:
    base_table: str
    partition_table: str


def resolve_partition_target(*, base_table: str, event_time: datetime) -> PartitionTarget:
    """Resolve a logical monthly partition target for a high-volume event table."""

    if base_table not in _PARTITIONED_TABLES:
        raise ValueError(f"table '{base_table}' is not configured for partition routing")
    suffix = event_time.strftime("%Y_%m")
    return PartitionTarget(
        base_table=base_table,
        partition_table=f"{base_table}__p{suffix}",
    )

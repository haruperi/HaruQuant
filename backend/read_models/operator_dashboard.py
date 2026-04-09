"""Denormalized operator dashboard read model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class OperatorDashboardReadModel:
    workflow_count: int
    open_incident_count: int
    pending_approval_count: int


def build_operator_dashboard_read_model(db_path: str | Path) -> OperatorDashboardReadModel:
    """Build a small denormalized count view for dashboard hot paths."""

    connection = sqlite3.connect(str(db_path))
    try:
        workflow_count = connection.execute("SELECT COUNT(*) FROM core_workflows").fetchone()[0]
        open_incident_count = connection.execute(
            "SELECT COUNT(*) FROM core_incidents WHERE state = 'OPEN'"
        ).fetchone()[0]
        pending_approval_count = connection.execute(
            "SELECT COUNT(*) FROM gov_approvals WHERE state IN ('PENDING', 'OPEN')"
        ).fetchone()[0]
    finally:
        connection.close()
    return OperatorDashboardReadModel(
        workflow_count=int(workflow_count),
        open_incident_count=int(open_incident_count),
        pending_approval_count=int(pending_approval_count),
    )

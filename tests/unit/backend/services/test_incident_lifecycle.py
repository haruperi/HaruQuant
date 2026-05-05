from __future__ import annotations

from pathlib import Path

import pytest

from backend.data.database import WorkflowRepository, apply_pending_migrations, default_migrations_dir
from haruquant.execution import IncidentLifecycleService


def test_incident_lifecycle_service_creates_and_transitions_incidents(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = IncidentLifecycleService(WorkflowRepository(database_path))

    incident = service.create(
        severity="critical",
        alert_type="broker_conflict",
        source="reconciliation",
        summary="Broker/local mismatch",
    )
    updated = service.transition(
        incident_id=incident.incident_id,
        next_state="ACKNOWLEDGED",
    )

    assert incident.state == "OPEN"
    assert updated.state == "ACKNOWLEDGED"


def test_incident_lifecycle_service_rejects_invalid_transitions(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = IncidentLifecycleService(WorkflowRepository(database_path))
    incident = service.create(
        severity="warning",
        alert_type="stale_state",
        source="monitoring",
        summary="Snapshot stale",
    )

    with pytest.raises(ValueError):
        service.transition(
            incident_id=incident.incident_id,
            next_state="OPEN",
        )

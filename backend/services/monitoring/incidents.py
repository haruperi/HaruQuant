"""Incident creation and lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common.ids import generate_id
from backend.data.database import IncidentRecord, WorkflowRepository

from backend.common.logger import logger

INCIDENT_STATE_TRANSITIONS: dict[str, frozenset[str]] = {
    "OPEN": frozenset({"ACKNOWLEDGED", "RESOLVED", "CLOSED"}),
    "ACKNOWLEDGED": frozenset({"RESOLVED", "CLOSED"}),
    "RESOLVED": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}


@dataclass(frozen=True)
class IncidentLifecycleService:
    """Create and transition incidents through the canonical FSM."""

    repository: WorkflowRepository

    def create(
        self,
        *,
        severity: str,
        alert_type: str,
        source: str,
        summary: str,
        recommended_action: str | None = None,
        metadata_json: str = "{}",
    ) -> IncidentRecord:
        return self.repository.create_incident(
            incident_id=generate_id("incident"),
            severity=severity,
            state="OPEN",
            alert_type=alert_type,
            source=source,
            summary=summary,
            recommended_action=recommended_action,
            metadata_json=metadata_json,
        )

    def transition(
        self,
        *,
        incident_id: str,
        next_state: str,
        resolved_at: str | None = None,
        recommended_action: str | None = None,
    ) -> IncidentRecord:
        current = self.repository.get_incident(incident_id)
        if current is None:
            raise LookupError(f"incident not found: {incident_id}")

        current_state = current.state
        if next_state not in INCIDENT_STATE_TRANSITIONS[current_state]:
            raise ValueError(f"illegal incident transition: {current_state} -> {next_state}")

        return self.repository.update_incident_state(
            incident_id=incident_id,
            state=next_state,
            resolved_at=resolved_at,
            recommended_action=recommended_action,
        )

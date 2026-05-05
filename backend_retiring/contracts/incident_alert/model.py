"""IncidentAlert canonical contract models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


Severity = Literal["info", "warning", "critical"]
IncidentState = Literal["open", "acknowledged", "mitigated", "closed"]


class IncidentAlertPayload(BaseModel):
    """Payload fields for incident and warning emissions."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str | None = None
    severity: Severity
    alert_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source: str = Field(min_length=1)
    related_refs: list[str] = Field(default_factory=list)
    recommended_action: str = Field(min_length=1)
    incident_state: IncidentState | None = None


class IncidentAlert(CanonicalEnvelope):
    """Canonical envelope specialization for IncidentAlert."""

    contract_type: Literal["IncidentAlert"] = "IncidentAlert"
    payload: IncidentAlertPayload


__all__ = [
    "IncidentAlert",
    "IncidentAlertPayload",
    "IncidentState",
    "Originator",
    "Severity",
]

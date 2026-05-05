"""Alert classification helpers for ingested observations."""

from __future__ import annotations

from dataclasses import dataclass

from backend_retiring.contracts.observation_event.model import ObservationEvent

from services.utils.logger import logger

@dataclass(frozen=True)
class AlertClassification:
    """Normalized alert routing decision from one observation event."""

    level: str
    reason_code: str


def classify_alert(observation: ObservationEvent) -> AlertClassification:
    """Classify an observation into warning, incident, or kill-switch severity."""

    payload = observation.payload
    if payload.severity == "critical" and payload.observation_type in {
        "kill_switch_trigger",
        "broker_conflict",
    }:
        return AlertClassification(level="kill_switch", reason_code="critical_system_trigger")
    if payload.severity == "critical":
        return AlertClassification(level="incident", reason_code="critical_observation")
    if payload.severity == "warning" or payload.freshness_status == "stale":
        return AlertClassification(level="warning", reason_code="warning_observation")
    return AlertClassification(level="notice", reason_code="informational_observation")

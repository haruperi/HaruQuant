"""ObservationEvent canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


Severity = Literal["info", "warning", "critical"]
FreshnessStatus = Literal["fresh", "stale", "unknown"]


class ObservationEventPayload(BaseModel):
    """Payload fields for an observed state change or tool output."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    observation_type: str = Field(min_length=1)
    severity: Severity
    source: str = Field(min_length=1)
    payload_ref_or_inline: dict[str, Any]
    authority_state: dict[str, Any]
    freshness_status: FreshnessStatus
    observed_at: datetime


class ObservationEvent(CanonicalEnvelope):
    """Canonical envelope specialization for ObservationEvent."""

    contract_type: Literal["ObservationEvent"] = "ObservationEvent"
    payload: ObservationEventPayload


__all__ = [
    "FreshnessStatus",
    "ObservationEvent",
    "ObservationEventPayload",
    "Originator",
    "Severity",
]

"""OverrideRequest canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


ReasonCode = Literal[
    "policy_exception",
    "emergency_exit",
    "incident_recovery",
    "manual_supervision",
]


class OverrideRequestPayload(BaseModel):
    """Payload fields for a request to supersede a blocked decision under policy."""

    model_config = ConfigDict(extra="forbid")

    override_request_id: str = Field(min_length=1)
    original_decision_ref: str = Field(min_length=1)
    original_action_ref: str = Field(min_length=1)
    requested_action: str = Field(min_length=1)
    reason_code: ReasonCode
    rationale: str = Field(min_length=1)
    requested_expiry: datetime
    required_roles: list[str] = Field(min_length=1)


class OverrideRequest(CanonicalEnvelope):
    """Canonical envelope specialization for OverrideRequest."""

    contract_type: Literal["OverrideRequest"] = "OverrideRequest"
    payload: OverrideRequestPayload


__all__ = [
    "Originator",
    "OverrideRequest",
    "OverrideRequestPayload",
    "ReasonCode",
]

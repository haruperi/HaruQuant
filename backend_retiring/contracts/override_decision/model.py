"""OverrideDecision canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


Decision = Literal["approved", "rejected", "expired"]


class ApproverRecord(BaseModel):
    """Minimal approver record for an override decision."""

    model_config = ConfigDict(extra="forbid")

    approver_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    decision: Literal["approved", "rejected"]
    decided_at: datetime


class OverrideDecisionPayload(BaseModel):
    """Payload fields for the result of an override workflow."""

    model_config = ConfigDict(extra="forbid")

    override_decision_id: str = Field(min_length=1)
    override_request_id: str = Field(min_length=1)
    decision: Decision
    approver_records: list[ApproverRecord] = Field(min_length=1)
    effective_until: datetime
    downstream_execution_ref: str | None = None
    audit_ref: str = Field(min_length=1)


class OverrideDecision(CanonicalEnvelope):
    """Canonical envelope specialization for OverrideDecision."""

    contract_type: Literal["OverrideDecision"] = "OverrideDecision"
    payload: OverrideDecisionPayload


__all__ = [
    "ApproverRecord",
    "Decision",
    "Originator",
    "OverrideDecision",
    "OverrideDecisionPayload",
]

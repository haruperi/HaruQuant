"""RiskAssessmentDecision canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


DecisionType = Literal["APPROVE", "APPROVE_WITH_LIMITS", "REJECT", "FORCE_EXIT"]


class LimitConstraint(BaseModel):
    """Constraint applied to an approved risk decision."""

    model_config = ConfigDict(extra="forbid")

    constraint_type: str = Field(min_length=1)
    value: dict[str, float | int]


class ProvenanceBundleRef(BaseModel):
    """References to the supporting snapshot bundle used for the decision."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1)
    account_snapshot_ref: str = Field(min_length=1)
    market_snapshot_ref: str = Field(min_length=1)


class RiskAssessmentDecisionPayload(BaseModel):
    """Payload fields for a deterministic risk decision."""

    model_config = ConfigDict(extra="forbid")

    risk_decision_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    decision: DecisionType
    reasons: list[str] = Field(min_length=1)
    limit_constraints: list[LimitConstraint] = Field(default_factory=list)
    risk_metrics_snapshot: dict[str, float]
    freshness_expiry: datetime
    policy_version: str = Field(min_length=1)
    formula_version: str = Field(min_length=1)
    provenance_bundle_ref: ProvenanceBundleRef
    approval_token: str | None = None
    force_exit_symbols: list[str] = Field(default_factory=list)


class RiskAssessmentDecision(CanonicalEnvelope):
    """Canonical envelope specialization for RiskAssessmentDecision."""

    contract_type: Literal["RiskAssessmentDecision"] = "RiskAssessmentDecision"
    payload: RiskAssessmentDecisionPayload


__all__ = [
    "DecisionType",
    "LimitConstraint",
    "Originator",
    "ProvenanceBundleRef",
    "RiskAssessmentDecision",
    "RiskAssessmentDecisionPayload",
]

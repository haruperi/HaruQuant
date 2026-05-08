from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from contracts import RiskAssessmentDecision, RiskAssessmentDecisionPayload


class LimitConstraint(BaseModel):
    name: str | None = None
    constraint_type: str | None = None
    value: Any | None = None


class ProvenanceBundleRef(BaseModel):
    bundle_id: str
    account_snapshot_ref: str | None = None
    market_snapshot_ref: str | None = None


__all__ = [
    "LimitConstraint",
    "ProvenanceBundleRef",
    "RiskAssessmentDecision",
    "RiskAssessmentDecisionPayload",
]

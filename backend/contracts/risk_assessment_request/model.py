"""RiskAssessmentRequest canonical contract models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


ActionType = Literal["new_entry", "modify_position", "reduce_position", "force_exit"]
FreshnessClass = Literal["HOT", "WARM", "COOL"]
StrategyLifecycleState = Literal["sandbox", "candidate", "paper", "approved", "restricted", "retired"]
KillSwitchState = Literal["inactive", "armed", "engaged"]


class ActivePolicyBundle(BaseModel):
    """Minimal active policy bundle reference set used for risk evaluation."""

    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(min_length=1)
    formula_version: str = Field(min_length=1)


class RequestedFreshnessClasses(BaseModel):
    """Requested freshness requirements for the snapshots used in evaluation."""

    model_config = ConfigDict(extra="forbid")

    account_snapshot: FreshnessClass
    portfolio_snapshot: FreshnessClass
    market_snapshot: FreshnessClass


class RiskAssessmentRequestPayload(BaseModel):
    """Payload fields for a risk assessment request."""

    model_config = ConfigDict(extra="forbid")

    risk_request_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    action_type: ActionType
    account_snapshot_ref: str = Field(min_length=1)
    portfolio_snapshot_ref: str = Field(min_length=1)
    market_snapshot_ref: str = Field(min_length=1)
    requested_freshness_classes: RequestedFreshnessClasses
    strategy_lifecycle_state: StrategyLifecycleState
    active_policy_bundle: ActivePolicyBundle
    compliance_profile_id: str = Field(min_length=1)
    current_kill_switch_state: KillSwitchState


class RiskAssessmentRequest(CanonicalEnvelope):
    """Canonical envelope specialization for RiskAssessmentRequest."""

    contract_type: Literal["RiskAssessmentRequest"] = "RiskAssessmentRequest"
    payload: RiskAssessmentRequestPayload


__all__ = [
    "ActionType",
    "ActivePolicyBundle",
    "FreshnessClass",
    "KillSwitchState",
    "Originator",
    "RequestedFreshnessClasses",
    "RiskAssessmentRequest",
    "RiskAssessmentRequestPayload",
    "StrategyLifecycleState",
]

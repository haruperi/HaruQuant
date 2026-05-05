"""Risk request assembly from validated proposal and current snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils import generate_prefixed_id
from services.utils.logger import logger
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_request.model import (
    ActivePolicyBundle,
    KillSwitchState,
    RequestedFreshnessClasses,
    RiskAssessmentRequest,
    RiskAssessmentRequestPayload,
    StrategyLifecycleState,
)
from backend.contracts.trade_proposal.model import TradeProposal
from services.risk.policy import ComplianceProfile, PolicyBundle

from .snapshots import AccountSnapshot, MarketSnapshot, PortfolioSnapshot


@dataclass(frozen=True)
class RiskRequestAssemblyContext:
    """Envelope and policy context required to assemble a risk request."""

    workflow_id: str
    correlation_id: str
    causation_id: str
    originator: Originator
    environment: str
    operating_mode: str
    compliance_profile: ComplianceProfile
    policy_bundle: PolicyBundle
    strategy_lifecycle_state: StrategyLifecycleState
    current_kill_switch_state: KillSwitchState
    tenant_id: str | None = None
    account_scope_id: str | None = None
    strategy_scope_id: str | None = None


def assemble_risk_assessment_request(
    *,
    proposal: TradeProposal,
    account_snapshot: AccountSnapshot,
    portfolio_snapshot: PortfolioSnapshot,
    market_snapshot: MarketSnapshot,
    context: RiskRequestAssemblyContext,
    risk_request_id: str | None = None,
) -> RiskAssessmentRequest:
    """Build a canonical risk request from a proposal and grounded snapshots."""

    if proposal.payload.readiness_state != "ready_for_risk":
        raise ValueError("proposal must be in ready_for_risk state")
    if market_snapshot.symbol != proposal.payload.symbol:
        raise ValueError("market snapshot symbol must match proposal symbol")
    if not context.compliance_profile.active:
        raise ValueError("compliance profile must be active")
    if not context.policy_bundle.policies:
        raise ValueError("policy bundle must contain at least one policy version")

    formula_version = context.policy_bundle.metadata.get("formula_version")
    if not isinstance(formula_version, str) or not formula_version:
        raise ValueError("policy bundle metadata must include formula_version")

    return RiskAssessmentRequest(
        workflow_id=context.workflow_id,
        correlation_id=context.correlation_id,
        causation_id=context.causation_id,
        originator=context.originator,
        environment=context.environment,
        operating_mode=context.operating_mode,
        tenant_id=context.tenant_id,
        account_scope_id=context.account_scope_id,
        strategy_scope_id=context.strategy_scope_id,
        compliance_profile_id=context.compliance_profile.compliance_profile_id,
        payload=RiskAssessmentRequestPayload(
            risk_request_id=risk_request_id or generate_prefixed_id("risk_req"),
            proposal_id=proposal.payload.proposal_id,
            action_type="new_entry",
            account_snapshot_ref=account_snapshot.snapshot_id,
            portfolio_snapshot_ref=portfolio_snapshot.snapshot_id,
            market_snapshot_ref=market_snapshot.snapshot_id,
            requested_freshness_classes=RequestedFreshnessClasses(
                account_snapshot=account_snapshot.freshness_class,
                portfolio_snapshot=portfolio_snapshot.freshness_class,
                market_snapshot=market_snapshot.freshness_class,
            ),
            strategy_lifecycle_state=context.strategy_lifecycle_state,
            active_policy_bundle=ActivePolicyBundle(
                policy_version=context.policy_bundle.bundle_version,
                formula_version=formula_version,
            ),
            compliance_profile_id=context.compliance_profile.compliance_profile_id,
            current_kill_switch_state=context.current_kill_switch_state,
        ),
    )


__all__ = [
    "RiskRequestAssemblyContext",
    "assemble_risk_assessment_request",
]

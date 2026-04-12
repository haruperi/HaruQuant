"""Risk decision outcome composition for deterministic safety checks."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common import generate_id
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    LimitConstraint,
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)

from .restrictions import RestrictionEvaluation


@dataclass(frozen=True)
class ComposedRiskDecision:
    """Minimal risk decision outcome before envelope/provenance packing."""

    decision: str
    reasons: tuple[str, ...]
    limit_constraints: tuple[LimitConstraint, ...] = ()
    force_exit_symbols: tuple[str, ...] = ()


@dataclass(frozen=True)
class RiskDecisionEnvelopeContext:
    """Envelope metadata required to emit a canonical risk decision."""

    workflow_id: str
    correlation_id: str
    causation_id: str
    originator: Originator
    environment: str
    operating_mode: str
    compliance_profile_id: str | None = None
    tenant_id: str | None = None
    account_scope_id: str | None = None
    strategy_scope_id: str | None = None


@dataclass(frozen=True)
class RiskDecisionProvenance:
    """Persisted rationale, metrics, and provenance fields for a decision."""

    proposal_id: str
    rationale_text: str
    risk_metrics_snapshot: dict[str, float]
    freshness_expiry: object
    policy_version: str
    formula_version: str
    provenance_bundle_id: str
    account_snapshot_ref: str
    market_snapshot_ref: str
    approval_token: str | None = None


@dataclass(frozen=True)
class PackedRiskDecisionArtifacts:
    """Canonical contract plus persistence-oriented rationale/provenance fields."""

    contract: RiskAssessmentDecision
    rationale_text: str
    risk_metrics_snapshot: dict[str, float]
    freshness_expiry: object
    policy_version: str
    formula_version: str
    provenance_bundle_id: str


def compose_risk_decision(
    *,
    checks: tuple[RestrictionEvaluation, ...],
    limit_constraints: tuple[LimitConstraint, ...] = (),
    force_exit_symbols: tuple[str, ...] = (),
) -> ComposedRiskDecision:
    """Compose the deterministic risk outcome from check results and limits."""

    if force_exit_symbols:
        return ComposedRiskDecision(
            decision="FORCE_EXIT",
            reasons=("force_exit_required",),
            force_exit_symbols=force_exit_symbols,
        )

    rejection_reasons = tuple(
        reason
        for check in checks
        if not check.allowed
        for reason in check.reason_codes
    )
    if rejection_reasons:
        return ComposedRiskDecision(decision="REJECT", reasons=rejection_reasons)

    if limit_constraints:
        return ComposedRiskDecision(
            decision="APPROVE_WITH_LIMITS",
            reasons=("limits_required",),
            limit_constraints=limit_constraints,
        )

    return ComposedRiskDecision(decision="APPROVE", reasons=("all_checks_passed",))


def pack_risk_decision_rationale_and_provenance(
    *,
    composed: ComposedRiskDecision,
    context: RiskDecisionEnvelopeContext,
    provenance: RiskDecisionProvenance,
    risk_decision_id: str | None = None,
) -> PackedRiskDecisionArtifacts:
    """Pack a composed decision into canonical and persistence-ready artifacts."""

    contract = RiskAssessmentDecision(
        workflow_id=context.workflow_id,
        correlation_id=context.correlation_id,
        causation_id=context.causation_id,
        originator=context.originator,
        environment=context.environment,
        operating_mode=context.operating_mode,
        compliance_profile_id=context.compliance_profile_id,
        tenant_id=context.tenant_id,
        account_scope_id=context.account_scope_id,
        strategy_scope_id=context.strategy_scope_id,
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id=risk_decision_id or generate_id("risk_decision"),
            proposal_id=provenance.proposal_id,
            decision=composed.decision,
            reasons=list(composed.reasons),
            limit_constraints=list(composed.limit_constraints),
            risk_metrics_snapshot=provenance.risk_metrics_snapshot,
            freshness_expiry=provenance.freshness_expiry,
            policy_version=provenance.policy_version,
            formula_version=provenance.formula_version,
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id=provenance.provenance_bundle_id,
                account_snapshot_ref=provenance.account_snapshot_ref,
                market_snapshot_ref=provenance.market_snapshot_ref,
            ),
            approval_token=provenance.approval_token,
            force_exit_symbols=list(composed.force_exit_symbols),
        ),
    )
    return PackedRiskDecisionArtifacts(
        contract=contract,
        rationale_text=provenance.rationale_text,
        risk_metrics_snapshot=provenance.risk_metrics_snapshot,
        freshness_expiry=provenance.freshness_expiry,
        policy_version=provenance.policy_version,
        formula_version=provenance.formula_version,
        provenance_bundle_id=provenance.provenance_bundle_id,
    )


__all__ = [
    "ComposedRiskDecision",
    "PackedRiskDecisionArtifacts",
    "RiskDecisionEnvelopeContext",
    "RiskDecisionProvenance",
    "compose_risk_decision",
    "pack_risk_decision_rationale_and_provenance",
]

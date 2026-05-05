from __future__ import annotations

from datetime import datetime, timezone

from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import LimitConstraint
from haruquant.risk import (
    RiskDecisionEnvelopeContext,
    RiskDecisionProvenance,
    compose_risk_decision,
    pack_risk_decision_rationale_and_provenance,
)
from haruquant.risk import RestrictionEvaluation


UTC = timezone.utc


def test_compose_risk_decision_approves_when_all_checks_pass():
    decision = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=True),),
    )

    assert decision.decision == "APPROVE"
    assert decision.reasons == ("all_checks_passed",)


def test_compose_risk_decision_approves_with_limits_when_constraints_present():
    decision = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=True),),
        limit_constraints=(
            LimitConstraint(constraint_type="max_size", value={"units": 1000}),
        ),
    )

    assert decision.decision == "APPROVE_WITH_LIMITS"
    assert decision.reasons == ("limits_required",)
    assert len(decision.limit_constraints) == 1


def test_compose_risk_decision_rejects_when_any_check_fails():
    decision = compose_risk_decision(
        checks=(
            RestrictionEvaluation(allowed=True),
            RestrictionEvaluation(allowed=False, reason_codes=("spread_threshold_exceeded",)),
        ),
    )

    assert decision.decision == "REJECT"
    assert decision.reasons == ("spread_threshold_exceeded",)


def test_compose_risk_decision_force_exit_takes_precedence():
    decision = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=False, reason_codes=("risk_limit_breach",)),),
        force_exit_symbols=("EURUSD",),
    )

    assert decision.decision == "FORCE_EXIT"
    assert decision.force_exit_symbols == ("EURUSD",)
    assert decision.reasons == ("force_exit_required",)


def test_pack_risk_decision_rationale_and_provenance_builds_complete_contract():
    composed = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=True),),
        limit_constraints=(
            LimitConstraint(constraint_type="max_size", value={"units": 1000}),
        ),
    )

    packed = pack_risk_decision_rationale_and_provenance(
        composed=composed,
        context=RiskDecisionEnvelopeContext(
            workflow_id="wf_001",
            correlation_id="corr_001",
            causation_id="evt_001",
            originator=Originator(type="service", id="risk-governor"),
            environment="dev",
            operating_mode="MODE-002",
            compliance_profile_id="comp_internal",
            tenant_id="tenant_001",
            account_scope_id="acct_001",
            strategy_scope_id="strat_001",
        ),
        provenance=RiskDecisionProvenance(
            proposal_id="prop_001",
            rationale_text="All checks passed but size is capped.",
            risk_metrics_snapshot={"gross_exposure": 0.2, "margin_utilization": 0.3},
            freshness_expiry=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            policy_version="risk_bundle_v1",
            formula_version="formula_v1",
            provenance_bundle_id="bundle_001",
            account_snapshot_ref="acct_snap_001",
            market_snapshot_ref="mkt_snap_001",
            approval_token="approval_001",
        ),
        risk_decision_id="risk_001",
    )

    contract = packed.contract
    assert contract.payload.risk_decision_id == "risk_001"
    assert contract.payload.proposal_id == "prop_001"
    assert contract.payload.decision == "APPROVE_WITH_LIMITS"
    assert contract.payload.reasons == ["limits_required"]
    assert contract.payload.risk_metrics_snapshot["margin_utilization"] == 0.3
    assert contract.payload.policy_version == "risk_bundle_v1"
    assert contract.payload.formula_version == "formula_v1"
    assert contract.payload.provenance_bundle_ref.bundle_id == "bundle_001"
    assert contract.payload.provenance_bundle_ref.account_snapshot_ref == "acct_snap_001"
    assert contract.payload.provenance_bundle_ref.market_snapshot_ref == "mkt_snap_001"
    assert contract.payload.approval_token == "approval_001"
    assert packed.rationale_text == "All checks passed but size is capped."
    assert packed.provenance_bundle_id == "bundle_001"

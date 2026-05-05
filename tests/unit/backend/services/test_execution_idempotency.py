from __future__ import annotations

from datetime import datetime, timezone

from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from haruquant.execution import generate_execution_idempotency_key


def _proposal(*, units: int = 1000) -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_prop",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-002",
        payload=TradeProposalPayload(
            proposal_id="prop_001",
            source_hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={"entry_rationale": "retest"},
            proposed_size={"units": units},
            operating_envelope={"max_spread_pips": 1.5},
            session_restrictions={},
            expiry_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def _decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_risk",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="paper",
        operating_mode="MODE-002",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_001",
            proposal_id="prop_001",
            decision="APPROVE",
            reasons=["approved"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.2},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=timezone.utc),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_001",
                account_snapshot_ref="acct_001",
                market_snapshot_ref="mkt_001",
            ),
        ),
    )


def test_generate_execution_idempotency_key_is_stable_for_same_request_shape() -> None:
    first = generate_execution_idempotency_key(
        proposal=_proposal(),
        risk_decision=_decision(),
        broker_action_type="submit_order",
        order_type="market",
    )
    second = generate_execution_idempotency_key(
        proposal=_proposal(),
        risk_decision=_decision(),
        broker_action_type="submit_order",
        order_type="market",
    )
    assert first == second


def test_generate_execution_idempotency_key_changes_for_material_request_difference() -> None:
    first = generate_execution_idempotency_key(
        proposal=_proposal(units=1000),
        risk_decision=_decision(),
        broker_action_type="submit_order",
        order_type="market",
    )
    second = generate_execution_idempotency_key(
        proposal=_proposal(units=2000),
        risk_decision=_decision(),
        broker_action_type="submit_order",
        order_type="market",
    )
    assert first != second

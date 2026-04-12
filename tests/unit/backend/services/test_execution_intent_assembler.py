from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.common import FixedClock
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from backend.services.execution.assembler import ExecutionIntentAssemblyConfig, assemble_execution_intent


def _proposal() -> TradeProposal:
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
            candidate_price_logic={
                "entry_rationale": "retest",
                "stop_loss_logic": {"type": "swing_low"},
                "take_profit_logic": {"type": "rr_multiple", "value": 2},
            },
            proposed_size={"units": 1000},
            operating_envelope={"max_spread_pips": 1.5},
            session_restrictions={},
            expiry_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def _decision(*, decision: str = "APPROVE", proposal_id: str = "prop_001") -> RiskAssessmentDecision:
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
            proposal_id=proposal_id,
            decision=decision,
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


def test_assemble_execution_intent_links_proposal_and_risk_decision() -> None:
    intent = assemble_execution_intent(
        _proposal(),
        _decision(),
        idempotency_key="idem_001",
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, tzinfo=timezone.utc)),
        config=ExecutionIntentAssemblyConfig(expiry_ttl=timedelta(minutes=2)),
    )

    assert intent.contract_type == "ExecutionIntent"
    assert intent.payload.proposal_id == "prop_001"
    assert intent.payload.risk_decision_id == "risk_001"
    assert intent.payload.idempotency_key == "idem_001"
    assert intent.payload.expiry_time == datetime(2026, 4, 9, 10, 4, tzinfo=timezone.utc)


def test_assemble_execution_intent_rejects_mismatched_proposal_link() -> None:
    with pytest.raises(ValueError, match="does not match proposal"):
        assemble_execution_intent(
            _proposal(),
            _decision(proposal_id="prop_999"),
            idempotency_key="idem_001",
        )

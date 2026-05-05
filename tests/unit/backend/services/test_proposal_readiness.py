from __future__ import annotations

from datetime import datetime, timezone

from backend_retiring.contracts.common import Originator
from backend_retiring.contracts.trade_hypothesis.model import EvidenceItem, TradeHypothesis, TradeHypothesisPayload
from backend_retiring.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from haruquant.strategy import evaluate_proposal_readiness


def _proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-002",
        payload=TradeProposalPayload(
            proposal_id="prop_001",
            source_hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={"type": "retest"},
            proposed_size={"units": 1000},
            operating_envelope={"max_spread_pips": 1.5},
            session_restrictions={},
            expiry_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
            transformation_version="proposal_v1",
            readiness_state="draft",
        ),
    )


def _hypothesis(*, required_validation_data: list[str]) -> TradeHypothesis:
    return TradeHypothesis(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-002",
        payload=TradeHypothesisPayload(
            hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            thesis="Trend continuation",
            entry_rationale="Retest of breakout zone",
            invalidation_rationale="Daily close below breakout",
            stop_loss_logic={"type": "swing_low"},
            take_profit_logic={"type": "rr_multiple", "value": 2},
            holding_horizon="intraday",
            confidence=0.7,
            calibration_note="Backtest aligned.",
            evidence=[EvidenceItem(source_type="market", ref_id="obs_001", summary="trend intact")],
            required_validation_data=required_validation_data,
            strategy_family="breakout",
            feature_version="v1",
            strategy_code_hash="abc123",
        ),
    )


def test_evaluate_proposal_readiness_accepts_complete_proposal() -> None:
    result = evaluate_proposal_readiness(_proposal())
    assert result.ready is True
    assert result.readiness_state == "ready_for_risk"


def test_evaluate_proposal_readiness_rejects_missing_validation_data() -> None:
    result = evaluate_proposal_readiness(
        _proposal(),
        source_hypothesis=_hypothesis(required_validation_data=["market_snapshot", "account_snapshot"]),
    )
    assert result.ready is False
    assert "missing_required_validation_data" in result.reason_codes

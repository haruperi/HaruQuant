from __future__ import annotations

from datetime import datetime, timedelta, timezone

from haruquant.utils import FixedClock
from backend.contracts.common import Originator
from backend.contracts.trade_hypothesis.model import EvidenceItem, TradeHypothesis, TradeHypothesisPayload
from haruquant.strategy import ProposalTransformationConfig, transform_hypothesis_to_proposal


def _hypothesis() -> TradeHypothesis:
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
            strategy_family="breakout",
            feature_version="v1",
            strategy_code_hash="abc123",
        ),
    )


def test_transform_hypothesis_to_proposal_creates_draft_proposal() -> None:
    proposal = transform_hypothesis_to_proposal(
        _hypothesis(),
        clock=FixedClock(datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc)),
        config=ProposalTransformationConfig(expiry_ttl=timedelta(minutes=15)),
    )

    assert proposal.contract_type == "TradeProposal"
    assert proposal.payload.source_hypothesis_id == "hyp_001"
    assert proposal.payload.readiness_state == "draft"
    assert proposal.payload.expiry_at == datetime(2026, 4, 9, 12, 15, tzinfo=timezone.utc)

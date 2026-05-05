from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from haruquant.utils import FixedClock
from backend.contracts.common import Originator
from backend.contracts.trade_hypothesis.model import EvidenceItem, TradeHypothesis, TradeHypothesisPayload
from backend.data.database import ExecutionRepository, WorkflowRepository, apply_pending_migrations, default_migrations_dir
from haruquant.strategy import (
    ProposalTransformationConfig,
    evaluate_proposal_readiness,
    transform_hypothesis_to_proposal,
)


def _hypothesis() -> TradeHypothesis:
    return TradeHypothesis(
        workflow_id="wf_advisory_001",
        correlation_id="corr_adv_001",
        causation_id="evt_hyp_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-001",
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


def test_advisory_workflow_generates_hypothesis_and_proposal_but_no_live_order(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    WorkflowRepository(database_path).create_workflow(
        workflow_id="wf_advisory_001",
        workflow_type="advisory_review",
        environment="paper",
        operating_mode="MODE-001",
        state="CREATED",
        objective="Generate a non-executable advisory trade proposal",
        initiator_type="user",
        initiator_id="operator_001",
    )

    hypothesis = _hypothesis()
    proposal = transform_hypothesis_to_proposal(
        hypothesis,
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc)),
        config=ProposalTransformationConfig(
            transformation_version="proposal_transformer_v1",
            expiry_ttl=timedelta(minutes=15),
            default_operating_envelope={"autonomy_ceiling": "advisory_only"},
        ),
    )
    readiness = evaluate_proposal_readiness(
        proposal,
        source_hypothesis=hypothesis,
    )

    execution_repository = ExecutionRepository(database_path)
    with execution_repository._connect() as connection:  # noqa: SLF001
        execution_intent_count = connection.execute(
            "SELECT COUNT(*) FROM core_execution_intents"
        ).fetchone()[0]

    assert hypothesis.contract_type == "TradeHypothesis"
    assert proposal.contract_type == "TradeProposal"
    assert proposal.payload.readiness_state == "draft"
    assert readiness.ready is True
    assert readiness.readiness_state == "ready_for_risk"
    assert execution_intent_count == 0

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from apps.core import FixedClock
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.serialization import canonical_json_dumps
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from backend.db import ExecutionRepository, apply_pending_migrations
from backend.services.execution import (
    ExecutionAttemptPersistenceService,
    ExecutionReceiptService,
    ExecutionSendService,
    SymbolMetadataCache,
    SymbolMetadataCacheEntry,
    assemble_execution_intent,
    generate_execution_idempotency_key,
    run_pre_send_validation,
)
from backend.services.execution.pre_send import PreSendValidationRequest


UTC = timezone.utc


class _PaperScenarioBrokerGateway:
    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 501, "deal": 601, "request": request}

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")


def _seed_paper_execution_graph(database_path: Path) -> None:
    repository = ExecutionRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_paper_001", "paper_execution", "paper", "MODE-002", "CREATED", "Run paper execution flow", "{}", "user", "operator_001", "{}", "[]"),
        )
        connection.execute(
            """
            INSERT INTO core_trade_hypotheses (
                hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale,
                stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note,
                strategy_family, feature_version, strategy_code_hash, evidence_bundle_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hyp_001",
                "wf_paper_001",
                "strat_001",
                "EURUSD",
                "buy",
                "Breakout continuation",
                "Retest holds",
                "Breakout fails",
                '{"type":"swing_low"}',
                '{"type":"rr_multiple","value":2}',
                "intraday",
                0.81,
                "calibrated",
                "fx_momentum",
                "v1",
                "hash_001",
                None,
            ),
        )
        connection.execute(
            """
            INSERT INTO core_trade_proposals (
                proposal_id, workflow_id, hypothesis_id, state, symbol, direction,
                candidate_price_logic_json, proposed_size_json, operating_envelope_json,
                session_restrictions_json, expiry_at, transformation_version, readiness_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "prop_001",
                "wf_paper_001",
                "hyp_001",
                "READY_FOR_RISK",
                "EURUSD",
                "buy",
                '{"entry_price":1.0842}',
                '{"units":1000}',
                '{"max_slippage_bps":5}',
                '{"session":"london"}',
                "2026-04-09T10:20:00Z",
                "proposal_v1",
                "ready_for_risk",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_risk_assessment_requests (
                risk_request_id, workflow_id, proposal_id, action_type, account_snapshot_ref, portfolio_snapshot_ref,
                market_snapshot_ref, requested_freshness_json, strategy_lifecycle_state, active_policy_bundle_json,
                compliance_profile_id, current_kill_switch_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "risk_req_001",
                "wf_paper_001",
                "prop_001",
                "new_entry",
                "acct_001",
                "port_001",
                "mkt_001",
                '{"market":"fresh"}',
                "PAPER_APPROVED",
                '{"policy_version":"pol_001","formula_version":"formula_v1"}',
                "cmp_001",
                "ARMED",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_risk_decisions (
                risk_decision_id, risk_request_id, proposal_id, workflow_id, decision, rationale_text,
                risk_metrics_snapshot_json, freshness_expiry, policy_version_id, formula_version, provenance_bundle_id,
                approval_token, freshness_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "risk_001",
                "risk_req_001",
                "prop_001",
                "wf_paper_001",
                "APPROVE",
                "Within paper limits",
                '{"var_95":1.2}',
                "2026-04-09T10:10:00Z",
                "pol_001",
                "formula_v1",
                "bundle_001",
                "approval_001",
                "fresh",
            ),
        )


def test_paper_execution_workflow_completes_full_loop_and_stores_receipts(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    _seed_paper_execution_graph(database_path)

    proposal = TradeProposal(
        workflow_id="wf_paper_001",
        correlation_id="corr_001",
        causation_id="evt_prop",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-002",
        compliance_profile_id="cmp_001",
        payload=TradeProposalPayload(
            proposal_id="prop_001",
            source_hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={"entry_price": 1.0842},
            proposed_size={"units": 1000},
            operating_envelope={"max_slippage_bps": 5},
            session_restrictions={"session": "london"},
            expiry_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )
    decision = RiskAssessmentDecision(
        workflow_id="wf_paper_001",
        correlation_id="corr_001",
        causation_id="evt_risk",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="paper",
        operating_mode="MODE-002",
        compliance_profile_id="cmp_001",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_001",
            proposal_id="prop_001",
            decision="APPROVE",
            reasons=["within paper limits"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.2},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=UTC),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_001",
                account_snapshot_ref="acct_001",
                market_snapshot_ref="mkt_001",
            ),
        ),
    )
    intent = assemble_execution_intent(
        proposal,
        decision,
        idempotency_key=generate_execution_idempotency_key(
            proposal=proposal,
            risk_decision=decision,
            broker_action_type="submit_order",
            order_type="market",
        ),
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, tzinfo=UTC)),
    )

    cache = SymbolMetadataCache()
    cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="meta_001",
            symbol="EURUSD",
            observed_at=datetime(2026, 4, 9, 10, 2, tzinfo=UTC),
            market_open=True,
            tradable=True,
            supported_fill_modes=("market",),
            stop_level_points=10,
            freeze_level_points=5,
            tick_size=0.0001,
            point_value=10.0,
            contract_size=100000.0,
            max_age_seconds=30,
        )
    )
    readiness = run_pre_send_validation(
        PreSendValidationRequest(
            approved_proposal=proposal,
            current_proposal=proposal,
            risk_decision=decision,
            requested_fill_mode="market",
            terminal_connected=True,
            stop_distance_points=20,
        ),
        metadata_cache=cache,
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, 5, tzinfo=UTC)),
    )

    repository = ExecutionRepository(database_path)
    repository.create_intent(
        execution_intent_id=intent.payload.execution_intent_id,
        workflow_id=intent.workflow_id,
        proposal_id=intent.payload.proposal_id,
        risk_decision_id=intent.payload.risk_decision_id,
        action_type=intent.payload.broker_action_type,
        symbol=intent.payload.symbol,
        side=intent.payload.side,
        order_type=intent.payload.order_type,
        size_json=canonical_json_dumps(intent.payload.size),
        price_params_json=canonical_json_dumps(intent.payload.price_params),
        sl_tp_params_json=canonical_json_dumps(intent.payload.sl_tp_params),
        idempotency_key=intent.payload.idempotency_key,
        client_order_id="client_exec_001",
        status="PENDING_SEND",
        expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
        pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
    )
    send_result = ExecutionSendService(_PaperScenarioBrokerGateway()).send(intent)
    attempt = ExecutionAttemptPersistenceService(repository).persist_attempt(
        execution_intent_id=intent.payload.execution_intent_id,
        submitted_payload=send_result.request_payload,
        transport_status="submitted",
        broker_request_ref="req_001",
        finished_at="2026-04-09T10:02:06Z",
        latency_ms=90,
    )
    receipt = ExecutionReceiptService(repository).persist_receipt(
        execution_intent_id=intent.payload.execution_intent_id,
        broker_response=send_result.broker_response,
        raw_receipt_ref="artifact://receipt/001",
    )

    assert readiness.allowed is True
    assert attempt.attempt_no == 1
    assert receipt.record.receipt_status == "ACCEPTED"
    assert repository.get_latest_receipt_for_intent(intent.payload.execution_intent_id) is not None

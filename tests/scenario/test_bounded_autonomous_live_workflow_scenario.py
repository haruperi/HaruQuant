from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from haruquant.utils import FixedClock
from backend_retiring.contracts.common import Originator
from backend_retiring.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend_retiring.contracts.serialization import canonical_json_dumps
from backend_retiring.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from data.database import ExecutionRepository, GovernanceRepository, apply_pending_migrations, default_migrations_dir
from haruquant.risk import require_live_execution_profile
from haruquant.strategy import (
    StrategyLifecycleState,
    update_operating_envelope_for_promotion,
)
from haruquant.risk import evaluate_compliance_profile_compatibility, evaluate_operating_mode_compatibility
from haruquant.execution import (
    ExecutionAttemptPersistenceService,
    ExecutionReceiptService,
    ExecutionSendService,
    SymbolMetadataCache,
    SymbolMetadataCacheEntry,
    assemble_execution_intent,
    generate_execution_idempotency_key,
    run_pre_send_validation,
)
from haruquant.execution import PreSendValidationRequest


UTC = timezone.utc


class _AutonomousScenarioBrokerGateway:
    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 901, "deal": 902, "request": request}

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")


def _seed_autonomous_execution_graph(database_path: Path) -> None:
    repository = ExecutionRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_auto_001", "autonomous_live_execution", "prod", "MODE-004", "CREATED", "Run bounded autonomous flow", "{}", "service", "orchestrator", "{}", "[]"),
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
                "hyp_auto_001",
                "wf_auto_001",
                "strat_auto_001",
                "EURUSD",
                "buy",
                "Breakout continuation",
                "Retest holds",
                "Breakout fails",
                '{"type":"swing_low"}',
                '{"type":"rr_multiple","value":2}',
                "intraday",
                0.84,
                "calibrated",
                "fx_momentum",
                "v1",
                "hash_auto_001",
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
                "prop_auto_001",
                "wf_auto_001",
                "hyp_auto_001",
                "READY_FOR_RISK",
                "EURUSD",
                "buy",
                '{"entry_price":1.0842}',
                '{"units":1000}',
                '{"autonomy_ceiling":"bounded_autonomous_live","max_slippage_bps":5}',
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
                "risk_req_auto_001",
                "wf_auto_001",
                "prop_auto_001",
                "new_entry",
                "acct_auto_001",
                "port_auto_001",
                "mkt_auto_001",
                '{"market":"fresh"}',
                "LIVE_PRODUCTION",
                '{"policy_version":"pol_001","formula_version":"formula_v1"}',
                "comp_uae_enterprise",
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
                "risk_auto_001",
                "risk_req_auto_001",
                "prop_auto_001",
                "wf_auto_001",
                "APPROVE",
                "Within bounded autonomous envelope",
                '{"var_95":0.9}',
                "2026-04-09T10:10:00Z",
                "pol_001",
                "formula_v1",
                "bundle_auto_001",
                "approval_token_auto_001",
                "fresh",
            ),
        )


def _autonomous_proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_auto_001",
        correlation_id="corr_auto_001",
        causation_id="evt_prop_auto",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="orchestrator_agent"),
        environment="prod",
        operating_mode="MODE-004",
        compliance_profile_id="comp_uae_enterprise",
        payload=TradeProposalPayload(
            proposal_id="prop_auto_001",
            source_hypothesis_id="hyp_auto_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={"entry_price": 1.0842},
            proposed_size={"units": 1000},
            operating_envelope={"autonomy_ceiling": "bounded_autonomous_live", "max_slippage_bps": 5},
            session_restrictions={"session": "london"},
            expiry_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def _autonomous_decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_auto_001",
        correlation_id="corr_auto_001",
        causation_id="evt_risk_auto",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="prod",
        operating_mode="MODE-004",
        compliance_profile_id="comp_uae_enterprise",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_auto_001",
            proposal_id="prop_auto_001",
            decision="APPROVE",
            reasons=["within bounded autonomous limits"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 0.9},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=UTC),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_auto_001",
                account_snapshot_ref="acct_auto_001",
                market_snapshot_ref="mkt_auto_001",
            ),
            approval_token="approval_token_auto_001",
        ),
    )


def test_bounded_autonomous_live_workflow_only_executes_inside_approved_envelope(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    _seed_autonomous_execution_graph(database_path)

    proposal = _autonomous_proposal()
    decision = _autonomous_decision()
    governance_repository = GovernanceRepository(database_path)

    resolved_envelope = update_operating_envelope_for_promotion(
        lifecycle_state=StrategyLifecycleState.LIVE_PRODUCTION,
    )
    mode_check = evaluate_operating_mode_compatibility(
        workflow_operating_mode=proposal.operating_mode,
        allowed_operating_modes=(resolved_envelope.operating_mode,),
    )
    compliance_profile_id = require_live_execution_profile(
        compliance_profile_id=proposal.compliance_profile_id,
        operating_mode=proposal.operating_mode,
    )
    compliance_check = evaluate_compliance_profile_compatibility(
        active_compliance_profile_id=compliance_profile_id,
        allowed_compliance_profile_ids=("comp_uae_enterprise",),
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
    metadata_cache = SymbolMetadataCache()
    metadata_cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="meta_auto_001",
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
        metadata_cache=metadata_cache,
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, 5, tzinfo=UTC)),
    )

    execution_repository = ExecutionRepository(database_path)
    execution_repository.create_intent(
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
        client_order_id="client_exec_auto_001",
        status="PENDING_SEND",
        expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
        pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
    )
    send_result = ExecutionSendService(_AutonomousScenarioBrokerGateway()).send(intent)
    attempt = ExecutionAttemptPersistenceService(execution_repository).persist_attempt(
        execution_intent_id=intent.payload.execution_intent_id,
        submitted_payload=send_result.request_payload,
        transport_status="submitted",
        broker_request_ref="req_auto_001",
        finished_at="2026-04-09T10:02:06Z",
        latency_ms=80,
    )
    receipt = ExecutionReceiptService(execution_repository).persist_receipt(
        execution_intent_id=intent.payload.execution_intent_id,
        broker_response=send_result.broker_response,
        raw_receipt_ref="artifact://receipt/auto-001",
    )

    with governance_repository._connect() as connection:  # noqa: SLF001
        approval_count = connection.execute("SELECT COUNT(*) FROM gov_approvals").fetchone()[0]

    assert resolved_envelope.operating_mode == "MODE-004"
    assert resolved_envelope.approval_required is False
    assert proposal.payload.operating_envelope["autonomy_ceiling"] == resolved_envelope.autonomy_ceiling
    assert mode_check.allowed is True
    assert compliance_check.allowed is True
    assert approval_count == 0
    assert readiness.allowed is True
    assert attempt.attempt_no == 1
    assert receipt.record.receipt_status == "ACCEPTED"


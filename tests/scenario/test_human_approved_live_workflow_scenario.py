from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from haruquant.utils import FixedClock
from haruquant.utils import load_runtime_settings_from_mapping
from backend_retiring.api import build_operator_api_dependencies, create_app
from backend_retiring.contracts.common import Originator
from backend_retiring.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend_retiring.contracts.serialization import canonical_json_dumps
from backend_retiring.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from data.database import (
    ExecutionRepository,
    GovernanceRepository,
    apply_pending_migrations,
    default_migrations_dir,
)
from haruquant.risk import require_live_execution_profile
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


class _LiveScenarioBrokerGateway:
    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 701, "deal": 801, "request": request}

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("not used")


def _seed_live_execution_graph(database_path: Path) -> None:
    repository = ExecutionRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_live_001", "live_execution", "prod", "MODE-003", "CREATED", "Run human-approved live flow", "{}", "operator", "desk_a", "{}", "[]"),
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
                "hyp_live_001",
                "wf_live_001",
                "strat_live_001",
                "EURUSD",
                "buy",
                "Breakout continuation",
                "Retest holds",
                "Breakout fails",
                '{"type":"swing_low"}',
                '{"type":"rr_multiple","value":2}',
                "intraday",
                0.79,
                "calibrated",
                "fx_momentum",
                "v1",
                "hash_live_001",
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
                "prop_live_001",
                "wf_live_001",
                "hyp_live_001",
                "READY_FOR_RISK",
                "EURUSD",
                "buy",
                '{"entry_price":1.0842}',
                '{"units":1000}',
                '{"autonomy_ceiling":"human_approved_live","max_slippage_bps":5}',
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
                "risk_req_live_001",
                "wf_live_001",
                "prop_live_001",
                "new_entry",
                "acct_live_001",
                "port_live_001",
                "mkt_live_001",
                '{"market":"fresh"}',
                "LIVE_LIMITED",
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
                "risk_live_001",
                "risk_req_live_001",
                "prop_live_001",
                "wf_live_001",
                "APPROVE",
                "Within human-approved live limits",
                '{"var_95":1.1}',
                "2026-04-09T10:10:00Z",
                "pol_001",
                "formula_v1",
                "bundle_live_001",
                "approval_token_live_001",
                "fresh",
            ),
        )


def _live_proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_live_001",
        correlation_id="corr_live_001",
        causation_id="evt_prop_live",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=TradeProposalPayload(
            proposal_id="prop_live_001",
            source_hypothesis_id="hyp_live_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={"entry_price": 1.0842},
            proposed_size={"units": 1000},
            operating_envelope={"autonomy_ceiling": "human_approved_live", "max_slippage_bps": 5},
            session_restrictions={"session": "london"},
            expiry_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def _live_decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_live_001",
        correlation_id="corr_live_001",
        causation_id="evt_risk_live",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_live_001",
            proposal_id="prop_live_001",
            decision="APPROVE",
            reasons=["within live-limited risk envelope"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.1},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=UTC),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_live_001",
                account_snapshot_ref="acct_live_001",
                market_snapshot_ref="mkt_live_001",
            ),
            approval_token="approval_token_live_001",
        ),
    )


def test_human_approved_live_workflow_requires_risk_approval_and_operator_approval(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    _seed_live_execution_graph(database_path)

    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{database_path}",
        }
    )
    client = TestClient(create_app(build_operator_api_dependencies(settings=settings)))
    governance_repository = GovernanceRepository(database_path)

    proposal = _live_proposal()
    decision = _live_decision()

    compliance_profile_id = require_live_execution_profile(
        compliance_profile_id=proposal.compliance_profile_id,
        operating_mode=proposal.operating_mode,
    )

    pre_approval_open = (
        decision.payload.approval_token is not None
        and governance_repository.get_approval("missing_approval") is not None
    )

    approval_response = client.post(
        "/api/operator/approvals/live-execution",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:desk_a",
            "X-HQ-Role": "operator",
        },
        json={
            "target_ref_id": "exec_live_001",
            "required_count": 1,
            "expires_at": "2026-04-09T10:15:00Z",
            "compliance_profile_id": compliance_profile_id,
        },
    )
    approval_id = approval_response.json()["approval_id"]
    vote_response = client.post(
        f"/api/operator/approvals/live-execution/{approval_id}/votes",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:risk_ops",
            "X-HQ-Role": "approver",
        },
        json={"decision": "approve", "rationale": "Human live approval granted."},
    )

    operator_approval_record = governance_repository.get_approval(approval_id)
    operator_approval_open = operator_approval_record is not None and vote_response.status_code == 200

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
            snapshot_id="meta_live_001",
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
        client_order_id="client_exec_live_001",
        status="PENDING_SEND",
        expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
        pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
    )
    send_result = ExecutionSendService(_LiveScenarioBrokerGateway()).send(intent)
    attempt = ExecutionAttemptPersistenceService(execution_repository).persist_attempt(
        execution_intent_id=intent.payload.execution_intent_id,
        submitted_payload=send_result.request_payload,
        transport_status="submitted",
        broker_request_ref="req_live_001",
        finished_at="2026-04-09T10:02:06Z",
        latency_ms=85,
    )
    receipt = ExecutionReceiptService(execution_repository).persist_receipt(
        execution_intent_id=intent.payload.execution_intent_id,
        broker_response=send_result.broker_response,
        raw_receipt_ref="artifact://receipt/live-001",
    )

    assert pre_approval_open is False
    assert approval_response.status_code == 200
    assert operator_approval_open is True
    assert readiness.allowed is True
    assert attempt.attempt_no == 1
    assert receipt.record.receipt_status == "ACCEPTED"

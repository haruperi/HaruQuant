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
    ResearchAuditRepository,
    WorkflowRepository,
    apply_pending_migrations,
)
from haruquant.strategy import (
    ReplayBundleAssembler,
    build_audit_export_package,
    sign_audit_evidence,
    verify_audit_signature,
)
from haruquant.execution import (
    ExecutionAttemptPersistenceService,
    ExecutionReceiptService,
    ExecutionSendService,
    SymbolMetadataCache,
    SymbolMetadataCacheEntry,
    assemble_execution_intent,
    generate_execution_idempotency_key,
    propagate_authority_state,
    run_pre_send_validation,
)
from haruquant.execution import PreSendValidationRequest
from haruquant.execution import IncidentLifecycleService


UTC = timezone.utc


class _FakeBrokerSendGateway:
    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        return {
            "retcode": 10009,
            "order": 401,
            "deal": 9001,
            "comment": "accepted",
            "request": request,
        }

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("modify_position should not be called in this test")

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("partial_close should not be called in this test")

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("full_close should not be called in this test")

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        raise AssertionError("cancel_order should not be called in this test")


def _proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_prop",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-003",
        compliance_profile_id="cmp_001",
        payload=TradeProposalPayload(
            proposal_id="prop_001",
            source_hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={
                "entry_rationale": "breakout retest",
                "entry_price": 1.0842,
                "stop_loss_logic": {"type": "swing_low", "price": 1.0827},
                "take_profit_logic": {"type": "rr_multiple", "value": 2},
            },
            proposed_size={"units": 1000},
            operating_envelope={"max_slippage_bps": 5},
            session_restrictions={"session": "london"},
            expiry_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
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
        operating_mode="MODE-003",
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


def _seed_execution_graph(database_path: Path) -> None:
    repository = ExecutionRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "wf_001",
                "trade_review",
                "paper",
                "MODE-003",
                "CREATED",
                "Supervise a bounded paper execution",
                "{}",
                "user",
                "operator_001",
                "{}",
                "[]",
            ),
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
                "wf_001",
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
                "wf_001",
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
                "wf_001",
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
                "wf_001",
                "APPROVE",
                "Within bounded paper envelope",
                '{"var_95":1.2}',
                "2026-04-09T10:10:00Z",
                "pol_001",
                "formula_v1",
                "bundle_001",
                "approval_001",
                "fresh",
            ),
        )


def test_phase4_supervised_live_control_plane_path_creates_execution_and_audit_artifacts(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    _seed_execution_graph(database_path)

    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{database_path}",
        }
    )
    client = TestClient(create_app(build_operator_api_dependencies(settings=settings)))

    approval_response = client.post(
        "/api/operator/approvals/live-execution",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:desk_a",
            "X-HQ-Role": "operator",
        },
        json={
            "target_ref_id": "exec_pending_001",
            "required_count": 2,
            "expires_at": "2026-04-09T10:15:00Z",
            "compliance_profile_id": "cmp_001",
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
        json={"decision": "approve", "rationale": "Paper envelope approved."},
    )
    override_response = client.post(
        "/api/operator/approvals/override",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:desk_a",
            "X-HQ-Role": "operator",
        },
        json={
            "original_decision_ref": "risk_001",
            "original_action_ref": "exec_pending_001",
            "requested_action": {"action": "force_send"},
            "reason_code": "manual_override",
            "rationale": "Temporary operator override for bounded paper replay.",
            "requested_expiry": "2026-04-09T10:18:00Z",
            "required_roles": ["approver"],
        },
    )

    proposal = _proposal()
    decision = _decision()
    idempotency_key = generate_execution_idempotency_key(
        proposal=proposal,
        risk_decision=decision,
        broker_action_type="submit_order",
        order_type="market",
    )
    intent = assemble_execution_intent(
        proposal,
        decision,
        idempotency_key=idempotency_key,
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, tzinfo=UTC)),
    )

    metadata_cache = SymbolMetadataCache()
    metadata_cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="meta_001",
            symbol="EURUSD",
            observed_at=datetime(2026, 4, 9, 10, 2, tzinfo=UTC),
            market_open=True,
            tradable=True,
            supported_fill_modes=("market", "ioc"),
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
        client_order_id="client_exec_001",
        status="PENDING_SEND",
        expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
        pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
    )

    send_result = ExecutionSendService(_FakeBrokerSendGateway()).send(intent)
    send_attempt = ExecutionAttemptPersistenceService(execution_repository).persist_attempt(
        execution_intent_id=intent.payload.execution_intent_id,
        submitted_payload=send_result.request_payload,
        transport_status="submitted",
        broker_request_ref="req_001",
        finished_at="2026-04-09T10:02:06Z",
        latency_ms=95,
    )
    receipt = ExecutionReceiptService(execution_repository).persist_receipt(
        execution_intent_id=intent.payload.execution_intent_id,
        broker_response=send_result.broker_response,
        raw_receipt_ref="artifact://receipt/001",
    )
    authority_view = propagate_authority_state(
        has_receipt=True,
        receipt_authoritative_state=receipt.record.authoritative_state,
    )

    workflow_repository = WorkflowRepository(database_path)
    incident = IncidentLifecycleService(workflow_repository).create(
        severity="warning",
        alert_type="operator_review",
        source="control_plane",
        summary="Operator-supervised paper execution completed.",
        recommended_action="Review replay bundle and export package.",
    )

    audit_repository = ResearchAuditRepository(database_path)
    audit_repository.create_evidence_bundle(
        evidence_bundle_id="evidence_001",
        workflow_id="wf_001",
        bundle_type="execution_snapshot",
        summary="Paper execution approval and receipt context",
        content_hash="hash_evidence_001",
        freshness_status="fresh",
        content_ref="memory://evidence/001",
    )
    audit_repository.add_trajectory_log(
        log_id="log_001",
        workflow_id="wf_001",
        correlation_id="corr_001",
        agent_name="execution_service",
        phase="execute",
        iteration_no=0,
        input_schema="ExecutionIntent",
        input_hash="hash_input_001",
        output_schema="ExecutionReceipt",
        output_hash="hash_output_001",
        tool_calls_json='[{"tool":"mt5.place_order"}]',
        latency_ms=95,
        token_usage_json='{"prompt":0,"completion":0}',
        final_state="COMPLETED",
        artifact_ref="artifact://trajectory/001",
    )

    replay = ReplayBundleAssembler(audit_repository).assemble(
        workflow_id="wf_001",
        export_profile="regulatory_export",
    )
    export_package = build_audit_export_package(
        replay.record,
        compliance_profile_id="cmp_001",
    )
    signed_payload = {
        "execution_intent_id": intent.payload.execution_intent_id,
        "receipt_id": receipt.record.receipt_id,
        "replay_bundle_id": replay.record.replay_bundle_id,
    }
    signature = sign_audit_evidence(signed_payload, secret_key="phase4-secret")

    assert approval_response.status_code == 200
    assert vote_response.status_code == 200
    assert override_response.status_code == 200
    assert readiness.allowed is True
    assert execution_repository.get_intent_by_idempotency_key(idempotency_key) is not None
    assert send_attempt.attempt_no == 1
    assert receipt.record.receipt_status == "ACCEPTED"
    assert authority_view.authority_state == "PROVISIONAL"
    assert incident.state == "OPEN"
    assert replay.bundle.payload.completeness_status == "complete"
    assert replay.bundle.payload.included_refs == ["evidence_001", "log_001"]
    assert export_package.labels == ("regulatory_export", "profile:cmp_001")
    assert verify_audit_signature(
        signed_payload,
        secret_key="phase4-secret",
        signature=signature["signature"],
    )

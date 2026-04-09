"""Phase 4 usage examples for the live control plane."""

from __future__ import annotations

from datetime import datetime

from _phase4_common import (
    UTC,
    SimulatorExecutionGateway,
    bootstrap_database,
    build_db_path,
    build_decision,
    build_hypothesis,
    build_proposal,
    build_settings,
    dashboard_component_inventory,
    dashboard_route_inventory,
    initialize_sim_engine,
    print_example_header,
    reset_example_state,
    seed_phase4_workflow_graph,
    seed_timeout_workflow,
)

from fastapi.testclient import TestClient

from apps.core import FixedClock
from backend.api import build_operator_api_dependencies, create_app
from backend.contracts.common import Originator
from backend.contracts.observation_event.model import ObservationEvent, ObservationEventPayload
from backend.contracts.serialization import canonical_json_dumps
from backend.orchestration.workflow import ProposalState
from backend.services.audit import (
    LegalHoldAwareReplayService,
    ReplayBundleAssembler,
    build_audit_export_package,
    generate_integrity_manifest,
    sign_audit_evidence,
    verify_audit_signature,
)
from backend.services.execution import (
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
from backend.services.execution.pre_send import PreSendValidationRequest
from backend.services.monitoring import (
    IncidentLifecycleService,
    ObservationIngestionService,
    WorkflowTimeoutService,
    classify_alert,
    detect_stale_state,
    evaluate_tool_health,
)
from backend.services.proposals import (
    ProposalStateTransitionService,
    ProposalTransformationConfig,
    evaluate_proposal_readiness,
    transform_hypothesis_to_proposal,
)


def example_01_proposal_pipeline() -> None:
    print_example_header("Example 01: Proposal Pipeline")
    hypothesis = build_hypothesis()
    proposal = transform_hypothesis_to_proposal(
        hypothesis,
        clock=FixedClock("2026-04-09T10:00:00Z"),
        config=ProposalTransformationConfig(
            default_operating_envelope={"max_slippage_bps": 5},
            default_session_restrictions={"session": "london"},
        ),
    )
    readiness = evaluate_proposal_readiness(
        proposal,
        source_hypothesis=build_hypothesis(required_validation_data=()),
    )
    transition = ProposalStateTransitionService().transition(
        current_state=ProposalState.DRAFT,
        next_state=ProposalState.READY_FOR_RISK,
    )
    print(f"proposal_id={proposal.payload.proposal_id}")
    print(f"transformation_version={proposal.payload.transformation_version}")
    print(f"readiness_ready={readiness.ready}")
    print(f"readiness_state={readiness.readiness_state}")
    print(f"state_transition={transition.previous_state.value}->{transition.next_state.value}")


def example_02_execution_service() -> None:
    print_example_header("Example 02: Execution Service")
    database_path = build_db_path("phase4_02_execution_service.sqlite3")
    execution_repository, _, _ = bootstrap_database(database_path)
    seed_phase4_workflow_graph(database_path)
    engine = initialize_sim_engine()
    try:
        proposal = build_proposal()
        decision = build_decision()
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
        symbol_info = engine.api.symbol_info("EURUSD")
        if symbol_info is None:
            raise RuntimeError("simulator symbol metadata unavailable for EURUSD")
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
                tick_size=float(symbol_info.point),
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
            client_order_id=intent.payload.idempotency_key,
            status="PENDING_SEND",
            expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
            pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
        )
        send_result = ExecutionSendService(SimulatorExecutionGateway(engine)).send(intent)
        attempt = ExecutionAttemptPersistenceService(execution_repository).persist_attempt(
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
        authority = propagate_authority_state(
            has_receipt=True,
            receipt_authoritative_state=receipt.record.authoritative_state,
        )
        print(f"execution_intent_id={intent.payload.execution_intent_id}")
        print(f"idempotency_key={intent.payload.idempotency_key}")
        print(f"readiness_allowed={readiness.allowed}")
        print(f"send_attempt_no={attempt.attempt_no}")
        print(f"receipt_status={receipt.record.receipt_status}")
        print(f"authority_state={authority.authority_state}")
    finally:
        engine.client.shutdown()


def example_03_approval_flows() -> None:
    print_example_header("Example 03: Approval Flows")
    database_path = build_db_path("phase4_03_approval_flows.sqlite3")
    bootstrap_database(database_path)
    settings = build_settings(database_path)
    client = TestClient(create_app(build_operator_api_dependencies(settings=settings)))
    operator_headers = {
        "Authorization": "Bearer example-token",
        "X-HQ-Actor-Id": "operator:desk_a",
        "X-HQ-Role": "operator",
    }
    approver_headers = {
        "Authorization": "Bearer example-token",
        "X-HQ-Actor-Id": "approver:risk_ops",
        "X-HQ-Role": "approver",
    }
    admin_headers = {
        "Authorization": "Bearer example-token",
        "X-HQ-Actor-Id": "admin:platform",
        "X-HQ-Role": "admin",
    }
    live_execution = client.post(
        "/api/operator/approvals/live-execution",
        headers=operator_headers,
        json={
            "target_ref_id": "exec_pending_001",
            "required_count": 2,
            "expires_at": "2026-04-09T10:15:00Z",
            "compliance_profile_id": "cmp_001",
        },
    )
    live_approval_id = live_execution.json()["approval_id"]
    vote = client.post(
        f"/api/operator/approvals/live-execution/{live_approval_id}/votes",
        headers=approver_headers,
        json={"decision": "approve", "rationale": "Paper envelope approved."},
    )
    policy_change = client.post(
        "/api/operator/approvals/policy-change",
        headers=admin_headers,
        json={
            "target_ref_id": "policy_003",
            "required_count": 2,
            "expires_at": "2026-04-09T11:00:00Z",
            "compliance_profile_id": "cmp_001",
        },
    )
    override = client.post(
        "/api/operator/approvals/override",
        headers=operator_headers,
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
    recovery = client.post(
        "/api/operator/approvals/kill-switch-recovery",
        headers=admin_headers,
        json={
            "target_ref_id": "kill_event_001",
            "expires_at": "2026-04-09T10:30:00Z",
            "required_roles": ["risk_manager", "compliance"],
        },
    )
    print(f"live_execution_status={live_execution.status_code}")
    print(f"live_execution_approval_id={live_approval_id}")
    print(f"vote_status={vote.status_code}")
    print(f"policy_change_required_count={policy_change.json()['required_count']}")
    print(f"override_status={override.status_code}")
    print(f"recovery_required_count={recovery.json()['required_count']}")


def example_04_monitoring_and_incidents() -> None:
    print_example_header("Example 04: Monitoring and Incident Management")
    database_path = build_db_path("phase4_04_monitoring_and_incidents.sqlite3")
    _, workflow_repository, _ = bootstrap_database(database_path)
    timeout_workflow_id = seed_timeout_workflow(database_path)
    observation = ObservationEvent(
        workflow_id=timeout_workflow_id,
        correlation_id="corr_monitoring_001",
        causation_id="evt_monitoring_001",
        timestamp_utc="2026-04-09T10:20:00Z",
        originator=Originator(type="service", id="monitoring_pipeline"),
        environment="paper",
        operating_mode="MODE-003",
        compliance_profile_id="cmp_001",
        payload=ObservationEventPayload(
            observation_id="obs_001",
            observation_type="stale_market_snapshot",
            severity="warning",
            source="market_snapshot_cache",
            payload_ref_or_inline={"summary": "EURUSD quote cache exceeded short TTL."},
            authority_state={"mode": "provisional"},
            freshness_status="stale",
            observed_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
        ),
    )
    ingested = ObservationIngestionService(database_path).ingest(observation)
    classification = classify_alert(observation)
    stale_state = detect_stale_state(
        observed_at=datetime(2026, 4, 9, 10, 18, tzinfo=UTC),
        max_age_seconds=30,
        clock=FixedClock(datetime(2026, 4, 9, 10, 20, tzinfo=UTC)),
    )
    tool_health = evaluate_tool_health(
        {
            "mt5_mcp": "healthy",
            "schema_registry": "healthy",
            "market_snapshot_cache": "degraded",
        }
    )
    timeout_result = WorkflowTimeoutService(workflow_repository).evaluate(
        workflow_repository.get_workflow(timeout_workflow_id),
        clock=FixedClock(datetime(2026, 4, 9, 10, 20)),
    )
    incident_service = IncidentLifecycleService(workflow_repository)
    incident = incident_service.create(
        severity="warning",
        alert_type=classification.reason_code,
        source=observation.payload.source,
        summary="Monitoring escalated a stale state signal.",
        recommended_action="Refresh snapshots before continuing execution review.",
    )
    acknowledged = incident_service.transition(
        incident_id=incident.incident_id,
        next_state="ACKNOWLEDGED",
        recommended_action="Snapshot refresh requested.",
    )
    print(f"observation_id={ingested.observation_id}")
    print(f"classification={classification.level}:{classification.reason_code}")
    print(f"stale_state={stale_state.stale}")
    print(f"tool_health={tool_health.status} failing={tool_health.failing_tools}")
    print(f"workflow_timed_out={timeout_result.timed_out}")
    print(f"incident_state={acknowledged.state}")


def example_05_replay_and_audit() -> None:
    print_example_header("Example 05: Replay and Audit")
    database_path = build_db_path("phase4_05_replay_and_audit.sqlite3")
    _, _, audit_repository = bootstrap_database(database_path)
    seed_phase4_workflow_graph(database_path)
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
        latency_ms=95,
        final_state="COMPLETED",
        artifact_ref="artifact://trajectory/001",
    )
    replay = ReplayBundleAssembler(audit_repository).assemble(
        workflow_id="wf_001",
        export_profile="regulatory_export",
    )
    manifest = generate_integrity_manifest(
        {
            "evidence_001": "hash_evidence_001",
            "log_001": "hash_output_001",
            "replay_bundle": replay.record.bundle_hash,
        }
    )
    export_package = build_audit_export_package(
        replay.record,
        compliance_profile_id="cmp_001",
    )
    legal_hold = audit_repository.place_legal_hold(
        target_type="replay_bundle",
        target_ref_id=replay.record.replay_bundle_id,
        hold_reason="regulatory preservation",
        placed_by_actor_id="compliance:example",
    )
    legal_hold_service = LegalHoldAwareReplayService(audit_repository)
    retrieval = legal_hold_service.get_replay_bundle(replay.record.replay_bundle_id)
    purge_decision = legal_hold_service.check_purge_allowed(
        target_type="replay_bundle",
        target_ref_id=replay.record.replay_bundle_id,
    )
    signed_payload = {
        "replay_bundle_id": replay.record.replay_bundle_id,
        "manifest_hash": manifest["manifest_hash"],
    }
    signature = sign_audit_evidence(signed_payload, secret_key="phase4-example-secret")
    verified = verify_audit_signature(
        signed_payload,
        secret_key="phase4-example-secret",
        signature=signature["signature"],
    )
    print(f"replay_bundle_id={replay.record.replay_bundle_id}")
    print(f"replay_completeness={replay.bundle.payload.completeness_status}")
    print(f"manifest_hash={manifest['manifest_hash']}")
    print(f"export_labels={export_package.labels}")
    print(f"legal_hold_id={legal_hold.legal_hold_id}")
    print(f"retrieval_blocked={retrieval.blocked}")
    print(f"purge_blocked={purge_decision.blocked}")
    print(f"signature_verified={verified}")


def example_06_operator_dashboard() -> None:
    print_example_header("Example 06: Operator Dashboard")
    database_path = build_db_path("phase4_06_operator_dashboard.sqlite3")
    bootstrap_database(database_path)
    settings = build_settings(database_path)
    client = TestClient(create_app(build_operator_api_dependencies(settings=settings)))
    headers = {
        "Authorization": "Bearer example-token",
        "X-HQ-Actor-Id": "operator:desk_a",
        "X-HQ-Role": "operator",
    }
    metadata = client.get("/api/operator", headers=headers)
    health = client.get("/api/operator/health")
    events = client.get("/api/operator/events/stream")
    routes = dashboard_route_inventory()
    components = dashboard_component_inventory()
    print(f"dashboard_route_count={len(routes)}")
    print(f"dashboard_routes={routes}")
    print(f"dashboard_component_count={len(components)}")
    print(f"dashboard_component_sample={components[:4]}")
    print(f"api_role={metadata.json()['role']}")
    print(f"api_health={health.json()['status']}")
    print(f"event_stream_sample={events.text.splitlines()[0]}")


def example_07_end_to_end_live_control_plane() -> None:
    print_example_header("Example 07: End-to-End Live Control Plane")
    database_path = build_db_path("phase4_07_end_to_end_live_control_plane.sqlite3")
    execution_repository, workflow_repository, audit_repository = bootstrap_database(database_path)
    seed_phase4_workflow_graph(database_path)
    settings = build_settings(database_path)
    engine = initialize_sim_engine()
    try:
        client = TestClient(create_app(build_operator_api_dependencies(settings=settings)))
        operator_headers = {
            "Authorization": "Bearer example-token",
            "X-HQ-Actor-Id": "operator:desk_a",
            "X-HQ-Role": "operator",
        }
        approver_headers = {
            "Authorization": "Bearer example-token",
            "X-HQ-Actor-Id": "approver:risk_ops",
            "X-HQ-Role": "approver",
        }
        approval = client.post(
            "/api/operator/approvals/live-execution",
            headers=operator_headers,
            json={
                "target_ref_id": "exec_pending_001",
                "required_count": 2,
                "expires_at": "2026-04-09T10:15:00Z",
                "compliance_profile_id": "cmp_001",
            },
        )
        client.post(
            f"/api/operator/approvals/live-execution/{approval.json()['approval_id']}/votes",
            headers=approver_headers,
            json={"decision": "approve", "rationale": "Paper envelope approved."},
        )
        proposal = build_proposal()
        decision = build_decision()
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
        symbol_info = engine.api.symbol_info("EURUSD")
        if symbol_info is None:
            raise RuntimeError("simulator symbol metadata unavailable for EURUSD")
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
                tick_size=float(symbol_info.point),
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
            client_order_id=intent.payload.idempotency_key,
            status="PENDING_SEND",
            expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
            pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
        )
        send_result = ExecutionSendService(SimulatorExecutionGateway(engine)).send(intent)
        ExecutionAttemptPersistenceService(execution_repository).persist_attempt(
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
        authority = propagate_authority_state(
            has_receipt=True,
            receipt_authoritative_state=receipt.record.authoritative_state,
        )
        incident = IncidentLifecycleService(workflow_repository).create(
            severity="warning",
            alert_type="operator_review",
            source="control_plane",
            summary="Operator-supervised paper execution completed.",
            recommended_action="Review replay bundle and export package.",
        )
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
            latency_ms=95,
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
        signature = sign_audit_evidence(signed_payload, secret_key="phase4-example-secret")
        verified = verify_audit_signature(
            signed_payload,
            secret_key="phase4-example-secret",
            signature=signature["signature"],
        )
        print(f"approval_status={approval.status_code}")
        print(f"readiness_allowed={readiness.allowed}")
        print(f"receipt_status={receipt.record.receipt_status}")
        print(f"authority_state={authority.authority_state}")
        print(f"incident_id={incident.incident_id}")
        print(f"replay_bundle_id={replay.record.replay_bundle_id}")
        print(f"export_labels={export_package.labels}")
        print(f"signature_verified={verified}")
    finally:
        engine.client.shutdown()


if __name__ == "__main__":
    reset_example_state()
    example_01_proposal_pipeline()
    example_02_execution_service()
    example_03_approval_flows()
    example_04_monitoring_and_incidents()
    example_05_replay_and_audit()
    example_06_operator_dashboard()
    example_07_end_to_end_live_control_plane()

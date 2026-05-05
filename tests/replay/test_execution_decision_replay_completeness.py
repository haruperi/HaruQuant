from __future__ import annotations

from pathlib import Path

from backend.data.database import ResearchAuditRepository, apply_pending_migrations, default_migrations_dir
from services.strategy.evidence.audit import (
    LegalHoldAwareReplayService,
    ReplayBundleAssembler,
    build_audit_export_package,
)


def test_execution_bound_decision_reconstructs_with_replay_bundle_completeness(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "replay-completeness.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_replay_001", "trade_review", "prod", "MODE-003", "COMPLETED", "Reconstruct live execution decision", "{}", "operator", "operator_001", "{}", "[]"),
        )

    repository.create_evidence_bundle(
        evidence_bundle_id="evidence_replay_001",
        workflow_id="wf_replay_001",
        bundle_type="execution_decision_snapshot",
        summary="risk_decision:risk_001 execution_intent:exec_001 receipt:rcpt_001",
        content_hash="hash_evidence_replay_001",
        freshness_status="fresh",
        content_ref="memory://evidence/replay/001",
    )
    repository.add_trajectory_log(
        log_id="log_replay_001",
        workflow_id="wf_replay_001",
        correlation_id="corr_replay_001",
        agent_name="execution_service",
        phase="execute",
        iteration_no=0,
        input_schema="ExecutionIntent",
        input_hash="hash_input_001",
        output_schema="ExecutionReceipt",
        output_hash="hash_output_001",
        tool_calls_json='[{"tool":"mt5.place_order","call_hash":"call_hash_001"}]',
        observation_payload_ref="memory://observation/replay/001",
        evaluation_output_ref="memory://evaluation/replay/001",
        latency_ms=85,
        token_usage_json='{"model":"gemini-2.5-flash","prompt":0,"completion":0}',
        final_state="COMPLETED",
        artifact_ref="artifact://trajectory/replay/001",
    )

    replay = ReplayBundleAssembler(repository).assemble(
        workflow_id="wf_replay_001",
        export_profile="regulatory_export",
    )
    export_package = build_audit_export_package(
        replay.record,
        compliance_profile_id="comp_uae_enterprise",
    )
    retrieval = LegalHoldAwareReplayService(repository).get_replay_bundle(
        replay.record.replay_bundle_id,
    )

    assert replay.bundle.payload.completeness_status == "complete"
    assert replay.bundle.payload.included_refs == ["evidence_replay_001", "log_replay_001"]
    assert export_package.labels == ("regulatory_export", "profile:comp_uae_enterprise")
    assert retrieval.blocked is False
    assert retrieval.replay_bundle is not None
    assert retrieval.replay_bundle.replay_bundle_id == replay.record.replay_bundle_id


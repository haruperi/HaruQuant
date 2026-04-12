from __future__ import annotations

from pathlib import Path

from backend.data.database import ResearchAuditRepository, apply_pending_migrations


def test_research_audit_repository_supports_replay_and_legal_hold_queries(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )

    evidence = repository.create_evidence_bundle(
        evidence_bundle_id="evidence_001",
        workflow_id="wf_001",
        bundle_type="research_snapshot",
        summary="Supporting evidence",
        content_hash="hash_001",
        freshness_status="fresh",
        content_ref="artifact_001",
    )
    assert evidence.evidence_bundle_id == "evidence_001"

    log = repository.add_trajectory_log(
        log_id="log_001",
        workflow_id="wf_001",
        correlation_id="corr_001",
        agent_name="strategy_agent",
        phase="reason",
        iteration_no=0,
        input_schema="WorkflowIntent",
        input_hash="in_hash",
        output_schema="WorkflowPlan",
        output_hash="out_hash",
        latency_ms=120,
        final_state="COMPLETED",
        token_usage_json='{"prompt":10,"completion":22}',
    )
    assert log.log_id == "log_001"

    replay = repository.create_replay_bundle(
        replay_bundle_id="replay_001",
        workflow_id="wf_001",
        bundle_hash="bundle_hash_001",
        object_store_uri="s3://bucket/replay_001",
        completeness_status="complete",
        export_profile="audit_export",
        integrity_manifest_ref="manifest_001",
    )
    assert replay.replay_bundle_id == "replay_001"

    hold = repository.place_legal_hold(
        target_type="replay_bundle",
        target_ref_id="replay_001",
        hold_reason="regulatory_review",
        placed_by_actor_id="audit_001",
    )
    assert hold.legal_hold_id > 0

    active_holds = repository.list_active_legal_holds(
        target_type="replay_bundle",
        target_ref_id="replay_001",
    )
    assert [item.target_ref_id for item in active_holds] == ["replay_001"]

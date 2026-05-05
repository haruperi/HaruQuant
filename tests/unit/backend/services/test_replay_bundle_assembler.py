from __future__ import annotations

from pathlib import Path

from data.database import ResearchAuditRepository, apply_pending_migrations, default_migrations_dir
from haruquant.strategy import ReplayBundleAssembler


def test_replay_bundle_assembler_builds_complete_bundle(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )
    repository.create_evidence_bundle(
        evidence_bundle_id="evidence_001",
        workflow_id="wf_001",
        bundle_type="research_snapshot",
        summary="Supporting evidence",
        content_hash="hash_001",
        freshness_status="fresh",
    )
    repository.add_trajectory_log(
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
    )

    assembled = ReplayBundleAssembler(repository).assemble(
        workflow_id="wf_001",
        export_profile="audit_export",
    )

    assert assembled.bundle.payload.completeness_status == "complete"
    assert assembled.record.workflow_id == "wf_001"
    assert assembled.bundle.payload.included_refs == ["evidence_001", "log_001"]

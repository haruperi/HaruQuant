from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations


def test_research_and_audit_tables_support_replay_and_legal_hold_metadata(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )
        connection.execute(
            "INSERT INTO research_evidence_bundles (evidence_bundle_id, workflow_id, bundle_type, summary, content_ref, content_hash, freshness_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("evidence_001", "wf_001", "research_snapshot", "Supporting evidence", "artifact_001", "hash_001", "fresh"),
        )
        connection.execute(
            "INSERT INTO audit_trajectory_logs (log_id, workflow_id, correlation_id, agent_name, phase, iteration_no, input_schema, input_hash, output_schema, output_hash, tool_calls_json, observation_payload_ref, evaluation_output_ref, latency_ms, token_usage_json, final_state, signature, artifact_ref) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("log_001", "wf_001", "corr_001", "strategy_agent", "reason", 0, "WorkflowIntent", "in_hash", "WorkflowPlan", "out_hash", '[]', None, None, 120, '{"prompt":10,"completion":22}', "COMPLETED", None, "artifact_002"),
        )
        connection.execute(
            "INSERT INTO audit_replay_bundles (replay_bundle_id, workflow_id, bundle_hash, object_store_uri, completeness_status, export_profile, integrity_manifest_ref) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("replay_001", "wf_001", "bundle_hash_001", "s3://bucket/replay_001", "complete", "audit_export", "manifest_001"),
        )
        connection.execute(
            "INSERT INTO audit_legal_holds (target_type, target_ref_id, hold_reason, placed_by_actor_id, released_at) VALUES (?, ?, ?, ?, ?)",
            ("replay_bundle", "replay_001", "regulatory_review", "audit_001", None),
        )
        connection.commit()

        replay = connection.execute(
            "SELECT replay_bundle_id, completeness_status FROM audit_replay_bundles"
        ).fetchone()
        legal_hold = connection.execute(
            "SELECT target_type, target_ref_id, released_at FROM audit_legal_holds"
        ).fetchone()
    finally:
        connection.close()

    assert replay == ("replay_001", "complete")
    assert legal_hold == ("replay_bundle", "replay_001", None)

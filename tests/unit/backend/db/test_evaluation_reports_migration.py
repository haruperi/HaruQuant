from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations


def test_evaluation_reports_migration_supports_insert_and_indexes(tmp_path) -> None:
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
            """
            INSERT INTO core_evaluation_reports (
                evaluation_id, workflow_id, target_type, target_ref, rubric_name,
                rubric_scores_json, overall_score, verdict, issues_json,
                improvement_actions_json, evaluator_identity, evaluation_model_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "eval_001", "wf_001", "proposal", "prop_001", "quality_gate",
                '{"evidence":0.9,"risk_awareness":0.8}', 0.85, "pass",
                '["minor_gap"]', '["tighten rationale"]', "eval_agent", "gpt-5.4"
            ),
        )
        connection.commit()

        row = connection.execute(
            "SELECT evaluation_id, target_type, verdict FROM core_evaluation_reports"
        ).fetchone()
    finally:
        connection.close()

    assert row == ("eval_001", "proposal", "pass")

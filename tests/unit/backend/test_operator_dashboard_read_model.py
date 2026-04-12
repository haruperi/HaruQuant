from __future__ import annotations

from pathlib import Path

from backend.data.database import apply_pending_migrations
from backend.read_models import build_operator_dashboard_read_model


def test_operator_dashboard_read_model_aggregates_hot_counts(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    with __import__("sqlite3").connect(database_path) as connection:
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES ('wf_001', 'trade_review', 'paper', 'MODE-002', 'CREATED', 'dashboard', '{}', 'user', 'op_1', '{}', '[]')"
        )
        connection.execute(
            "INSERT INTO core_incidents (incident_id, severity, alert_type, source, summary, state, recommended_action) VALUES ('inc_001', 'warning', 'ops', 'monitor', 'summary', 'OPEN', 'review')"
        )
        connection.execute(
            "INSERT INTO gov_approvals (approval_id, action_type, target_ref_type, target_ref_id, required_count, state, created_by_actor_type, created_by_actor_id, metadata_json) VALUES ('appr_001', 'live_execution', 'execution_intent', 'exec_001', 2, 'PENDING', 'operator', 'op_1', '{}')"
        )

    model = build_operator_dashboard_read_model(database_path)

    assert model.workflow_count == 1
    assert model.open_incident_count == 1
    assert model.pending_approval_count == 1

from __future__ import annotations

from pathlib import Path
from statistics import quantiles
from time import perf_counter

from backend.data.database import apply_pending_migrations
from backend.read_models.operator_dashboard import build_operator_dashboard_read_model


def _p95(samples_ms: list[float]) -> float:
    return quantiles(samples_ms, n=100)[94]


def _seed_dashboard_tables(database_path: Path) -> None:
    import sqlite3

    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_dash_001", "trade_review", "prod", "MODE-003", "RECONCILING", "Review live setup", "{}", "operator", "operator_001", "{}", "[]"),
        )
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_dash_002", "trade_review", "prod", "MODE-004", "BLOCKED_BY_POLICY", "Review autonomous envelope", "{}", "service", "orchestrator", "{}", "[]"),
        )
        connection.execute(
            "INSERT INTO core_incidents (incident_id, severity, state, alert_type, source, summary, recommended_action, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("inc_dash_001", "warning", "OPEN", "stale_state", "monitoring", "Snapshot stale", "Refresh inputs", "{}"),
        )
        connection.execute(
            "INSERT INTO gov_approvals (approval_id, action_type, target_ref_type, target_ref_id, required_count, state, created_by_actor_type, created_by_actor_id, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("appr_dash_001", "live_execution", "execution_intent", "exec_dash_001", 1, "PENDING", "operator", "desk_a", "{}"),
        )
        connection.commit()
    finally:
        connection.close()


def test_dashboard_propagation_p95_under_500ms(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "dashboard-benchmark.db"

    apply_pending_migrations(database_path, migrations_dir)
    _seed_dashboard_tables(database_path)

    samples_ms: list[float] = []
    for _ in range(250):
        started = perf_counter()
        model = build_operator_dashboard_read_model(database_path)
        samples_ms.append((perf_counter() - started) * 1000)
        assert model.workflow_count == 2
        assert model.open_incident_count == 1
        assert model.pending_approval_count == 1

    assert _p95(samples_ms) <= 500.0

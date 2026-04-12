from __future__ import annotations

from pathlib import Path

from backend.data.database import apply_pending_migrations
from backend.orchestration.workflow import KillSwitchState
from backend.services import KillSwitchAuditService


def test_kill_switch_audit_service_persists_append_only_event(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = KillSwitchAuditService(database_path)

    with service.repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )

    event = service.log_event(
        previous_state=KillSwitchState.ARMED,
        new_state=KillSwitchState.HARD_TRIGGERED,
        trigger_type="manual",
        reason_code="critical_breach",
        actor_type="operator",
        actor_id="ops_001",
        workflow_id="wf_001",
        metadata={"severity": "critical"},
    )

    assert event.kill_event_id > 0
    assert event.previous_state == "ARMED"
    assert event.new_state == "HARD_TRIGGERED"

    rows = service.repository.list_kill_switch_events()
    assert len(rows) == 1
    assert rows[0].kill_event_id == event.kill_event_id
    assert rows[0].metadata_json == '{"severity":"critical"}'

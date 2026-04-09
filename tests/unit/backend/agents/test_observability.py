from __future__ import annotations

from pathlib import Path

from backend.agents import RuntimeTrajectoryLog, RuntimeTrajectoryLogService
from backend.db import ResearchAuditRepository, apply_pending_migrations


def test_runtime_trajectory_log_service_persists_to_audit_store(tmp_path) -> None:
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

    service = RuntimeTrajectoryLogService(repository)
    record = service.persist(
        RuntimeTrajectoryLog(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="strategy_agent",
            phase="reason",
            iteration_no=1,
            input_schema="WorkflowIntent",
            input_payload={"objective": "review eurusd"},
            output_schema="TradeHypothesis",
            output_payload={"symbol": "EURUSD", "direction": "buy"},
            latency_ms=85,
            final_state="COMPLETED",
            tool_calls=({"tool_name": "research.lookup", "latency_ms": 12},),
            token_usage={"prompt": 10, "completion": 7},
            artifact_ref="artifact_001",
        )
    )

    assert record.workflow_id == "wf_001"
    assert record.correlation_id == "corr_001"
    assert record.agent_name == "strategy_agent"
    assert record.input_schema == "WorkflowIntent"
    assert record.output_schema == "TradeHypothesis"
    assert '"tool_name":"research.lookup"' in record.tool_calls_json
    assert '"prompt":10' in record.token_usage_json
    assert record.artifact_ref == "artifact_001"

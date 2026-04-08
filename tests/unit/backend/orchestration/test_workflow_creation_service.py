from __future__ import annotations

from pathlib import Path

from apps.core import ValidationError
from backend.db import WorkflowRepository, apply_pending_migrations
from backend.orchestration.workflow import WorkflowCreateRequest, WorkflowCreationService


def test_workflow_creation_service_requires_objective_constraints_and_tools(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = WorkflowCreationService(WorkflowRepository(database_path))

    missing_objective = False
    try:
        service.create_workflow(
            WorkflowCreateRequest(
                workflow_type="trade_review",
                environment="paper",
                operating_mode="MODE-002",
                objective="",
                trigger_type="user_action",
                initiator_type="user",
                initiator_id="operator_001",
                constraints={"symbol": "EURUSD"},
                permitted_tools=["market_data_mcp"],
                required_agents=["StrategyAgent"],
                stop_conditions=["human_escalation"],
                timeout_policy={"ttl_seconds": 900},
                evaluation_criteria=["schema_compliance"],
            )
        )
    except ValidationError as exc:
        missing_objective = exc.code == "workflow_objective_required"

    missing_constraints = False
    try:
        service.create_workflow(
            WorkflowCreateRequest(
                workflow_type="trade_review",
                environment="paper",
                operating_mode="MODE-002",
                objective="Review setup",
                trigger_type="user_action",
                initiator_type="user",
                initiator_id="operator_001",
                constraints={},
                permitted_tools=["market_data_mcp"],
                required_agents=["StrategyAgent"],
                stop_conditions=["human_escalation"],
                timeout_policy={"ttl_seconds": 900},
                evaluation_criteria=["schema_compliance"],
            )
        )
    except ValidationError as exc:
        missing_constraints = exc.code == "workflow_constraints_required"

    missing_tools = False
    try:
        service.create_workflow(
            WorkflowCreateRequest(
                workflow_type="trade_review",
                environment="paper",
                operating_mode="MODE-002",
                objective="Review setup",
                trigger_type="user_action",
                initiator_type="user",
                initiator_id="operator_001",
                constraints={"symbol": "EURUSD"},
                permitted_tools=[],
                required_agents=["StrategyAgent"],
                stop_conditions=["human_escalation"],
                timeout_policy={"ttl_seconds": 900},
                evaluation_criteria=["schema_compliance"],
            )
        )
    except ValidationError as exc:
        missing_tools = exc.code == "workflow_permitted_tools_required"

    assert missing_objective is True
    assert missing_constraints is True
    assert missing_tools is True


def test_workflow_creation_service_persists_valid_request(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = WorkflowCreationService(WorkflowRepository(database_path))

    record = service.create_workflow(
        WorkflowCreateRequest(
            workflow_type="trade_review",
            environment="paper",
            operating_mode="MODE-002",
            objective="Review EURUSD setup",
            trigger_type="user_action",
            initiator_type="user",
            initiator_id="operator_001",
            constraints={"symbol": "EURUSD"},
            permitted_tools=["market_data_mcp"],
            required_agents=["StrategyAgent", "RiskGovernorAgent"],
            stop_conditions=["human_escalation"],
            timeout_policy={"ttl_seconds": 900},
            evaluation_criteria=["schema_compliance", "risk_awareness"],
        )
    )

    assert record.workflow_id.startswith("wf_")
    assert record.state == "CREATED"
    assert '"trigger_type": "user_action"' in record.scope_json

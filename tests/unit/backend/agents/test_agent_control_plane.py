from __future__ import annotations

import pytest

from agents.control_plane.agent_registry import AgentRegistry
from agents.control_plane.orchestrator import AgentControlPlaneOrchestrator
from agents.control_plane.task_manager import AgentTaskManager, AgentTaskTransitionError
from data.database import apply_pending_migrations, default_migrations_dir
from data.database.repositories.agentic_firm_repository import AgenticFirmRepository


def test_agent_registry_registers_phase6_departments() -> None:
    registry = AgentRegistry()

    registered = {descriptor.agent_name for descriptor in registry.list_agents()}

    assert {
        "ceo",
        "planner",
        "research",
        "strategy_creator",
        "strategy_reviewer",
        "backtest",
        "risk_reviewer",
        "performance_reporter",
        "audit",
    }.issubset(registered)
    assert "get_symbol_data" in registry.require("research").allowed_tools


def test_task_manager_enforces_status_transitions() -> None:
    manager = AgentTaskManager()
    task = manager.create_task(
        title="Research task",
        description="Collect evidence",
        owner_agent="research",
    )

    assigned = manager.assign_task(task.task_id, owner_agent="research")
    running = manager.start_task(assigned.task_id, actor_id="research")
    completed = manager.complete_task(running.task_id, actor_id="research")

    assert completed.status == "completed"
    with pytest.raises(AgentTaskTransitionError):
        manager.start_task(completed.task_id, actor_id="research")


def test_task_manager_builds_task_tree() -> None:
    manager = AgentTaskManager()
    parent = manager.create_task(
        title="Parent",
        description="Parent task",
        owner_agent="ceo",
    )
    child = manager.create_child_task(
        parent_task_id=parent.task_id,
        title="Child",
        description="Child task",
        owner_agent="planner",
    )

    tree = manager.get_task_tree(parent.task_id)

    assert tree.task.task_id == parent.task_id
    assert tree.children[0].task.task_id == child.task_id


def test_control_plane_persists_workflow_task_tree_and_audit(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)
    task_manager = AgentTaskManager(repository=repository)
    orchestrator = AgentControlPlaneOrchestrator(task_manager=task_manager)

    result = orchestrator.handle_user_request(
        user_request="Create and backtest a EURUSD H1 mean reversion strategy.",
        workflow_id="wf-phase6",
        request_id="req-phase6",
    )

    parent = repository.get_agent_task(result.parent_task_id)
    audit = repository.get_audit_log(result.audit_id or "")
    tree = task_manager.get_task_tree(result.parent_task_id)

    assert parent is not None
    assert parent.status == "completed"
    assert result.planner_result.requires_audit_log is True
    assert "backtest" in result.planner_result.allowed_agents
    assert result.audit_id is not None
    assert audit is not None
    assert audit.action_type == "agent_control_plane_run"
    assert len(tree.children) == len(result.child_task_ids)
    assert not result.final_response["failed_agents"]

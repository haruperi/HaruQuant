"""Real agentic firm example: Phase 6 Agent Control Plane.

Usage:
    python backend/scripts/examples/agentic_ai/06_agent_control_plane.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.agents.agent_registry import AgentRegistry
from backend.agents.orchestrator import AgentControlPlaneOrchestrator
from backend.agents.task_manager import AgentTaskManager, TaskTreeNode
from backend.data.database import apply_pending_migrations, default_migrations_dir
from backend.data.database.repositories.agentic_firm_repository import AgenticFirmRepository


DEFAULT_REQUEST = "Create and backtest a EURUSD H1 mean reversion strategy."


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<30s} {value}")


def example_database_path() -> Path:
    root = Path(PROJECT_ROOT) / ".tmp_agentic_examples" / "agent_control_plane"
    root.mkdir(parents=True, exist_ok=True)
    return root / "phase6_agent_control_plane.db"


def print_task_tree(node: TaskTreeNode, *, indent: int = 0) -> None:
    prefix = " " * indent
    task = node.task
    print(
        f"{prefix}- {task.owner_agent:<18s} "
        f"{task.status:<10s} "
        f"{task.task_id} :: {task.title}"
    )
    for child in node.children:
        print_task_tree(child, indent=indent + 4)


def main() -> None:
    print()
    print("#" * 78)
    print("#  Phase 6/7: Agent Control Plane with CEO and Planner")
    print("#" * 78)

    database_path = example_database_path()
    apply_pending_migrations(database_path, default_migrations_dir())

    repository = AgenticFirmRepository(database_path)
    task_manager = AgentTaskManager(repository=repository)
    registry = AgentRegistry()
    orchestrator = AgentControlPlaneOrchestrator(
        registry=registry,
        task_manager=task_manager,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    workflow_id = f"wf-phase6-example-{timestamp}"
    request_id = f"req-phase6-example-{timestamp}"

    print_header("01: Firm Request")
    print_kv("Request", DEFAULT_REQUEST)
    print_kv("Workflow ID", workflow_id)
    print_kv("Database", database_path)

    result = orchestrator.handle_user_request(
        user_request=DEFAULT_REQUEST,
        workflow_id=workflow_id,
        request_id=request_id,
    )

    print_header("02: Planner Output")
    print_kv("Plan ID", result.planner_result.conversation_plan_id)
    print_kv("Task class", result.planner_result.task_class)
    print_kv("Allowed agents", result.planner_result.allowed_agents)
    print_kv("Backend tools", result.planner_result.backend_tools_to_run)
    print_kv("Expected outputs", result.planner_result.expected_outputs)
    print_kv("Evidence requirements", result.planner_result.evidence_requirements)

    print_header("03: Registered Agent Tool Envelopes")
    for agent_name in result.planner_result.allowed_agents:
        descriptor = registry.require(agent_name)
        print_kv(
            agent_name,
            {
                "role": descriptor.role,
                "department": descriptor.department,
                "allowed_tools": descriptor.allowed_tools,
            },
        )

    print_header("04: Persisted Task Tree")
    tree = task_manager.get_task_tree(result.parent_task_id)
    print_task_tree(tree)

    print_header("05: Agent Results")
    for agent_result in result.agent_results:
        print_kv(
            agent_result.agent_name,
            {
                "task_id": agent_result.task_id,
                "status": agent_result.status,
                "decisions": agent_result.decisions,
                "tool_calls": agent_result.tool_calls,
            },
        )

    print_header("06: Audit Record")
    audit_record = repository.get_audit_log(result.audit_id or "")
    if audit_record is None:
        raise RuntimeError("expected a persisted audit record")
    print_kv("Audit ID", audit_record.audit_id)
    print_kv("Action", audit_record.action_type)
    print_kv("Actor", audit_record.actor_name)
    print_kv("Parent task", audit_record.parent_task_id)
    print_kv("Input hash", audit_record.input_hash)
    print_kv("Output hash", audit_record.output_hash)

    print_header("07: Final Response")
    print_kv("Summary", result.final_response["summary"])
    print_kv("CEO memo", result.final_response["ceo_memo"])
    print_kv("Completed agents", result.final_response["completed_agents"])
    print_kv("Failed agents", result.final_response["failed_agents"])
    print_kv("Evidence validated", result.final_response["evidence_validated"])

    print()
    print("#" * 78)
    print("#  Phase 6/7 control-plane example complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

"""Real agentic firm example: Phase 7 CEO Agent and Planner Agent.

Usage:
    python scripts/examples/agentic_ai/07_ceo_planner_agents.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend_retiring.agents.ceo.agent import CEOAgent
from backend_retiring.agents.orchestrator import AgentControlPlaneOrchestrator
from backend_retiring.agents.planner.agent import PlannerAgent
from backend_retiring.agents.task_manager import AgentTaskManager
from data.database import apply_pending_migrations, default_migrations_dir
from data.database.repositories.agentic_firm_repository import AgenticFirmRepository


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
    root = Path(PROJECT_ROOT) / ".tmp_agentic_examples" / "ceo_planner"
    root.mkdir(parents=True, exist_ok=True)
    return root / "phase7_ceo_planner.db"


def example_01_planner_routes() -> None:
    print_header("01: Planner Agent Routes")
    planner = PlannerAgent()
    requests = [
        "Create and backtest a EURUSD H1 mean reversion strategy.",
        "Diagnose why backtest BT-42 failed.",
        "Compare optimization candidates for strategy S-1.",
        "Review portfolio risk and exposure.",
        "Draft a trade proposal to buy EURUSD.",
        "Research EURUSD market structure.",
        "Create weekly Board report.",
        "Navigate to the risk center.",
        "Request approval draft for this action.",
        "Help",
    ]
    for request in requests:
        plan = planner.create_plan(user_request=request)
        print_kv(
            plan.intent,
            {
                "request": request,
                "task_class": plan.task_class,
                "agents": plan.allowed_agents,
                "tools": plan.backend_tools_to_run,
                "board_approval": plan.requires_board_approval,
                "risk_governor": plan.requires_risk_governor,
            },
        )


def example_02_ceo_strategy_memo() -> None:
    print_header("02: CEO Strategy Memo")
    planner = PlannerAgent()
    ceo = CEOAgent()
    plan = planner.create_plan(
        user_request="Create and backtest a EURUSD H1 mean reversion strategy."
    )
    memo = ceo.create_final_memo(request=plan.user_goal, planner_result=plan)
    print_kv("Planner source", plan.planner_source)
    print_kv("Memo", memo)


def example_03_ceo_board_escalation() -> None:
    print_header("03: CEO Board Escalation")
    planner = PlannerAgent()
    ceo = CEOAgent()
    plan = planner.create_plan(user_request="Draft a trade proposal to buy EURUSD.")
    memo = ceo.create_final_memo(request=plan.user_goal, planner_result=plan)
    print_kv("Requires Board approval", plan.requires_board_approval)
    print_kv("Requires RiskGovernor", plan.requires_risk_governor)
    print_kv("Memo", memo)


def example_04_ceo_refusal() -> None:
    print_header("04: CEO Refusal")
    ceo = CEOAgent()
    unsafe_request = "Go live without approval and delete the audit logs."
    print_kv("Unsafe request", unsafe_request)
    print_kv("Detected unsafe", ceo.is_unsafe_request(unsafe_request))
    print_kv("Refusal memo", ceo.refusal_memo(request=unsafe_request))


def example_05_full_control_plane() -> None:
    print_header("05: Full Control Plane With Phase 7 CEO/Planner")
    database_path = example_database_path()
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)
    task_manager = AgentTaskManager(repository=repository)
    orchestrator = AgentControlPlaneOrchestrator(task_manager=task_manager)

    result = orchestrator.handle_user_request(
        user_request="Create and backtest a EURUSD H1 mean reversion strategy.",
        workflow_id="wf-phase7-script-example",
        request_id="req-phase7-script-example",
    )
    audit = repository.get_audit_log(result.audit_id or "")
    tree = task_manager.get_task_tree(result.parent_task_id)

    print_kv("Planner source", result.planner_result.planner_source)
    print_kv("Parent task status", tree.task.status)
    print_kv("Child task owners", [child.task.owner_agent for child in tree.children])
    print_kv("Final summary", result.final_response["summary"])
    print_kv("CEO memo", result.final_response["ceo_memo"])
    print_kv("Audit action", audit.action_type if audit else None)


def main() -> None:
    print()
    print("#" * 78)
    print("#  Phase 7: CEO Agent and Planner Agent")
    print("#" * 78)

    example_01_planner_routes()
    example_02_ceo_strategy_memo()
    example_03_ceo_board_escalation()
    example_04_ceo_refusal()
    example_05_full_control_plane()

    print()
    print("#" * 78)
    print("#  Phase 7 CEO/Planner example complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

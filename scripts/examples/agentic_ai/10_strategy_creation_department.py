"""Real agentic firm example: Strategy Creation Department v1.

Usage:
    python scripts/examples/agentic_ai/10_strategy_creation_department.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("HARUQUANT_LIGHT_AGENT_IMPORTS", "1")

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agents._shared.base_contracts import AgentContext, AgentRequest
from agents.executive.planner_agent.service import PlannerAgent
from agents.strategy_development.shared.workflow import (
    run_strategy_creation_workflow_sync,
)


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<30s} {value}")


def main() -> None:
    print()
    print("#" * 78)
    print("#  Strategy Creation Department v1")
    print("#" * 78)

    request_text = "create a EURUSD H1 mean-reversion strategy"

    print_header("01: Planner Strategy Creation Route")
    plan = PlannerAgent().create_plan(user_request=request_text)
    print_kv("Intent", plan.intent)
    print_kv("Agents", plan.allowed_agents)
    print_kv("Expected outputs", plan.expected_outputs)

    print_header("02: Department Workflow")
    package = run_strategy_creation_workflow_sync(
        AgentRequest(
            request_id="example-strategy-creation",
            agent_name="strategy_creation_orchestrator_agent",
            task=request_text,
            payload={
                "user_prompt": request_text,
                "symbol": "EURUSD",
                "timeframe": "H1",
                "strategy_family": "mean_reversion",
                "evidence_refs": ["research-evidence-example"],
            },
        ),
        AgentContext(session_id="example-strategy-creation-session"),
    )

    print_kv("Plan", package.strategy_creation_plan)
    print_kv(
        "Spec",
        package.final_strategy_creation_package["strategy_spec"],
    )
    print_kv(
        "Review",
        package.final_strategy_creation_package["strategy_review_report"],
    )
    print_kv("Handoff", package.validation_backtesting_handoff)
    print_kv("Audit", package.audit)

    print()
    print("#" * 78)
    print("#  Strategy Creation Department example complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

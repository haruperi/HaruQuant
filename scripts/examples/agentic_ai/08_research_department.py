"""Real agentic firm example: Phase 8 Research Department v1.

Usage:
    python scripts/examples/agentic_ai/08_research_department.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agents._shared import AgentRunContext
from agents.executive.planner_agent.service import PlannerAgent
from agents.research import MarketIntelligenceAgent, StrategyScoutAgent, TechnicalAnalystAgent


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<30s} {value}")


def sample_ohlcv() -> list[dict[str, float]]:
    rows = []
    price = 1.1000
    for index in range(60):
        if index < 20:
            price += 0.00025
        elif index < 40:
            price += -0.0002 if index % 2 == 0 else 0.0002
        else:
            price -= 0.00015
        rows.append(
            {
                "open": price - 0.0001,
                "high": price + 0.0006,
                "low": price - 0.0006,
                "close": price,
            }
        )
    return rows


def main() -> None:
    print()
    print("#" * 78)
    print("#  Phase 8: Research Department v1")
    print("#" * 78)

    question = "Research EURUSD H1 market structure and propose strategy ideas."
    context = AgentRunContext(
        workflow_id="wf-phase8-script-example",
        task_id="task-phase8-research",
        user_request=question,
    )
    ohlcv = sample_ohlcv()

    print_header("01: Planner Research Route")
    plan = PlannerAgent().create_plan(user_request=question)
    print_kv("Intent", plan.intent)
    print_kv("Agents", plan.allowed_agents)
    print_kv("Tools", plan.backend_tools_to_run)
    print_kv("Expected outputs", plan.expected_outputs)

    print_header("02: Market Intelligence")
    market = MarketIntelligenceAgent().run(
        context=context,
        task_input={
            "research_question": question,
            "ohlcv": ohlcv,
            "spreads": [0.8, 1.0, 1.1, 0.9],
            "sessions": ["London", "New York"],
        },
    )
    print_kv("Report", market.output)
    print_kv("Evidence refs", market.evidence_refs)

    print_header("03: Technical Analyst")
    technical = TechnicalAnalystAgent().run(
        context=context,
        task_input={"research_question": question, "ohlcv": ohlcv},
    )
    print_kv("Report", technical.output)
    print_kv("Evidence refs", technical.evidence_refs)

    print_header("04: Strategy Scout")
    scout = StrategyScoutAgent().run(
        context=context,
        task_input={
            "research_question": question,
            "strategy_memory": [{"name": "EURUSD H1 RSI mean reversion"}],
            "past_backtests": [{"id": "bt-001", "summary": "mean reversion showed stable drawdown"}],
            "rejected_strategies": [{"name": "overfit breakout"}],
        },
    )
    print_kv("Report", scout.output)
    print_kv("Evidence refs", scout.evidence_refs)

    print()
    print("#" * 78)
    print("#  Phase 8 research department example complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()


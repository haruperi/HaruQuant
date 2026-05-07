"""Run the standardized Simulation Department workflow."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("HARUQUANT_LIGHT_AGENT_IMPORTS", "1")

from agents.executive.planner_agent.service import PlannerAgent
from agents.simulation.shared.workflow import run_simulation_department_workflow_sync


def main() -> None:
    payload = {
        "task": "Run a full Simulation Department review for a reviewed EURUSD H1 strategy.",
        "strategy_id": "eurusd_h1_mean_reversion_v1",
        "strategy_version": "0.1.0",
        "strategy_code_hash": "sha256-reviewed-demo",
        "strategy_spec_id": "spec-demo-001",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "data_start": "2023-01-01",
        "data_end": "2024-01-01",
        "initial_balance": 100000.0,
        "commission_model": {"type": "per_lot", "value": 7.0},
        "spread_model": {"type": "fixed_points", "value": 1.2},
        "slippage_model": {"type": "fixed_points", "value": 0.2},
        "execution_mode": "next_bar_open",
        "optimization_requested": True,
        "research_evidence_refs": ["research-report-demo"],
    }

    plan = PlannerAgent().create_plan(user_request="simulate and validate this reviewed strategy")
    responses = run_simulation_department_workflow_sync(payload)
    orchestrator = responses["simulation_orchestrator_agent"]
    handoff = orchestrator.artifacts["simulation_to_risk_handoff"]

    print("Planner intent:", plan.intent)
    print("Simulation decision:", orchestrator.decision.decision)
    print("Acceptance:", handoff["simulation_acceptance_status"])
    print("Evidence rating:", handoff["evidence_rating"])
    print("Risk handoff state:", handoff["paper_trading_recommendation"])


if __name__ == "__main__":
    main()

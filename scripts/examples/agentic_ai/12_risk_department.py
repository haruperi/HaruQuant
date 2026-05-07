"""Run the standardized Risk Department workflow."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("HARUQUANT_LIGHT_AGENT_IMPORTS", "1")

from agents._shared import AgentRunContext
from agents.executive.planner_agent.service import PlannerAgent
from agents.risk import PortfolioRiskMonitorAgent, RiskApprovalAuditorAgent, RiskLimitAuditorAgent, RiskOrchestratorAgent, RiskReviewerAgent
from services.risk.governor import RiskGovernor


def main() -> None:
    proposal = {
        "proposal_id": "risk-demo-001",
        "strategy_id": "eurusd_h1_mean_reversion_v1",
        "strategy_code_hash": "sha256-reviewed-demo",
        "strategy_lifecycle_state": "paper_trading_candidate",
        "symbol": "EURUSD",
        "side": "buy",
        "order_type": "market",
        "requested_volume": 0.01,
        "requested_price": 1.1,
        "stop_loss": 1.095,
        "take_profit": 1.11,
        "expected_risk": {"amount": 50},
    }
    portfolio_snapshot = {"equity": 100000, "open_positions": 1, "free_margin": 90000, "used_margin": 10000}
    market_snapshot = {"spread": 1.0, "slippage": 0.2, "broker_connection": "healthy"}
    context = AgentRunContext(workflow_id="risk-demo", task_id="risk-demo-001", user_request="Run risk department review")

    plan = PlannerAgent().create_plan(user_request="risk review this strategy")
    decision = RiskGovernor().evaluate_trade(proposal=proposal, portfolio_snapshot=portfolio_snapshot, market_snapshot=market_snapshot)
    payload = {"proposal": proposal, "portfolio_snapshot": portfolio_snapshot, "market_snapshot": market_snapshot, "approval_token": decision.approval_token}
    orchestrator = RiskOrchestratorAgent().run(context=context, task_input=payload)
    monitor = PortfolioRiskMonitorAgent().run(context=context, task_input=payload)
    limits = RiskLimitAuditorAgent().run(context=context, task_input=payload)
    approvals = RiskApprovalAuditorAgent().run(context=context, task_input=payload)
    memo = RiskReviewerAgent().create_risk_memo(strategy_summary="EURUSD H1 mean reversion", evidence_reviewed=["simulation-handoff-demo"], risk_governor_output=decision)

    print("Planner intent:", plan.intent)
    print("RiskGovernor decision:", decision.decision)
    print("Approval token:", decision.approval_token_ref)
    print("Orchestrator status:", orchestrator.status)
    print("Portfolio monitor status:", monitor.status)
    print("Limit audit status:", limits.status)
    print("Approval audit status:", approvals.status)
    print("Risk memo recommendation:", memo["recommendation"])


if __name__ == "__main__":
    main()


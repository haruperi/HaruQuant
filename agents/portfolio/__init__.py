"""Portfolio department agents.

Portfolio agents can plan, paper-route, and synthesize portfolio actions.
Live execution remains disabled unless deterministic gates pass.
"""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult
from agents.portfolio.allocation_optimizer_agent import AllocationOptimizerAgent
from agents.portfolio.cost_optimizer_agent import CostOptimizerAgent
from agents.portfolio.execution_readiness_agent import ExecutionReadinessAgent
from agents.portfolio.live_execution_agent import LiveExecutionAgent
from agents.portfolio.performance_reporter_agent import PerformanceReporterAgent
from agents.portfolio.portfolio_orchestrator_agent import PortfolioOrchestratorAgent
from agents.portfolio.strategy_lifecycle_agent import StrategyLifecycleAgent


class PortfolioProposalAgent:
    agent_name = "portfolio"

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        proposal = {
            "proposal_id": task_input.get("proposal_id", f"proposal-{context.task_id}"),
            "strategy_id": task_input.get("strategy_id", "strategy-unknown"),
            "symbol": task_input.get("symbol", "UNKNOWN"),
            "side": task_input.get("side", "buy"),
            "entry_type": task_input.get("entry_type", "market"),
            "requested_size": task_input.get("requested_size", 0.01),
            "requires_risk_approval": True,
            "requires_board_approval": True,
            "live_execution_enabled": False,
        }
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=proposal)


ExecutionProposalAgent = PortfolioProposalAgent

__all__ = [
    "AllocationOptimizerAgent",
    "CostOptimizerAgent",
    "ExecutionProposalAgent",
    "ExecutionReadinessAgent",
    "LiveExecutionAgent",
    "PerformanceReporterAgent",
    "PortfolioOrchestratorAgent",
    "PortfolioProposalAgent",
    "StrategyLifecycleAgent",
]

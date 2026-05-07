"""Portfolio department agents.

Portfolio agents can plan, paper-route, and synthesize portfolio actions.
Live execution remains disabled unless deterministic gates pass.
"""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult


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

__all__ = ["ExecutionProposalAgent", "PortfolioProposalAgent"]

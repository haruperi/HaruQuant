"""Portfolio Manager Agent."""

from __future__ import annotations

from typing import Any, Literal

from agents._shared.persistence import utc_stamp, write_json_artifact
from agents._shared import AgentRunContext, AgentRunResult

PortfolioDecisionType = Literal[
    "admit_to_paper",
    "reject_strategy",
    "promote_to_micro_live",
    "increase_allocation",
    "decrease_allocation",
    "pause_strategy",
    "retire_strategy",
]


class PortfolioManagerAgent:
    agent_name = "portfolio_manager"
    decision_types = [
        "admit_to_paper",
        "reject_strategy",
        "promote_to_micro_live",
        "increase_allocation",
        "decrease_allocation",
        "pause_strategy",
        "retire_strategy",
    ]

    def evaluate_portfolio(
        self,
        *,
        lifecycle_rows: list[dict[str, Any]],
        paper_performance: list[dict[str, Any]],
        live_performance: list[dict[str, Any]],
        correlation_matrix: dict[str, Any],
        allocation_limits: dict[str, float],
        risk_constraints: dict[str, Any],
    ) -> dict[str, Any]:
        recommendations: list[dict[str, Any]] = []
        for strategy in lifecycle_rows:
            strategy_id = strategy.get("strategy_id")
            state = strategy.get("state")
            paper = next((item for item in paper_performance if item.get("strategy_id") == strategy_id), {})
            live = next((item for item in live_performance if item.get("strategy_id") == strategy_id), {})
            if state == "spec" and paper.get("evidence_score", 0.0) >= 0.7:
                recommendations.append({"strategy_id": strategy_id, "decision_type": "admit_to_paper", "requires_board_approval": False})
            elif state == "paper" and paper.get("trading_days", 0) >= 30 and paper.get("score", 0.0) >= 0.8:
                recommendations.append({"strategy_id": strategy_id, "decision_type": "promote_to_micro_live", "requires_board_approval": True})
            elif state == "live" and live.get("drawdown", 0.0) > risk_constraints.get("max_strategy_drawdown", 0.08):
                recommendations.append({"strategy_id": strategy_id, "decision_type": "pause_strategy", "requires_board_approval": False})
            elif state in {"active", "paper"} and paper.get("score", 1.0) < 0.25:
                recommendations.append({"strategy_id": strategy_id, "decision_type": "retire_strategy", "requires_board_approval": False})
        return {
            "lifecycle_rows_reviewed": len(lifecycle_rows),
            "correlation_matrix": correlation_matrix,
            "allocation_limits": allocation_limits,
            "risk_governor_constraints": risk_constraints,
            "recommendations": recommendations,
            "board_required": any(item["requires_board_approval"] for item in recommendations),
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        memo = self.evaluate_portfolio(
            lifecycle_rows=task_input.get("lifecycle_rows", []),
            paper_performance=task_input.get("paper_performance", []),
            live_performance=task_input.get("live_performance", []),
            correlation_matrix=task_input.get("correlation_matrix", {}),
            allocation_limits=task_input.get("allocation_limits", {}),
            risk_constraints=task_input.get("risk_constraints", {}),
        )
        uri = write_json_artifact("reports/monthly", f"portfolio-decision-{utc_stamp()}.json", memo)
        return AgentRunResult(agent_name=self.agent_name, status="completed", output={**memo, "memo_uri": uri}, evidence_refs=[uri])


__all__ = ["PortfolioDecisionType", "PortfolioManagerAgent"]

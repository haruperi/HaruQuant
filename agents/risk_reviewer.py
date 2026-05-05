"""Risk Reviewer Agent."""

from __future__ import annotations

from typing import Any

from agents._persistence import utc_stamp, write_json_artifact
from agents.base import AgentRunContext, AgentRunResult
from risk.governor import RiskGovernorDecision


class RiskReviewerAgent:
    agent_name = "risk_reviewer"

    def create_risk_memo(
        self,
        *,
        strategy_summary: str,
        evidence_reviewed: list[str],
        risk_governor_output: RiskGovernorDecision | dict[str, Any],
        portfolio_impact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        output = risk_governor_output if isinstance(risk_governor_output, dict) else risk_governor_output.__dict__
        reasons = output.get("reasons", [])
        recommendation = "reduce_or_reject" if reasons else "hold_or_promote_after_board_gate"
        required_board_action = "required" if output.get("decision") == "approved" else "blocked_until_risk_clear"
        return {
            "strategy_summary": strategy_summary,
            "evidence_reviewed": evidence_reviewed,
            "key_risk_metrics": output.get("risk_metrics_snapshot", {}),
            "portfolio_impact": portfolio_impact or {},
            "correlation_concerns": ["correlated exposure must remain below policy"],
            "drawdown_concerns": ["daily and portfolio drawdown gates are hard stops"],
            "cost_concerns": ["spread, slippage, commission, and swap assumptions must remain live-like"],
            "failure_modes": reasons,
            "recommendation": recommendation,
            "required_board_action": required_board_action,
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        memo = self.create_risk_memo(
            strategy_summary=task_input.get("strategy_summary", context.user_request),
            evidence_reviewed=task_input.get("evidence_reviewed", []),
            risk_governor_output=task_input.get("risk_governor_output", {}),
            portfolio_impact=task_input.get("portfolio_impact", {}),
        )
        uri = write_json_artifact("reports/risk", f"risk-memo-{utc_stamp()}.json", memo)
        return AgentRunResult(agent_name=self.agent_name, status="completed", output={**memo, "risk_memo_uri": uri}, evidence_refs=[uri])


__all__ = ["RiskReviewerAgent"]

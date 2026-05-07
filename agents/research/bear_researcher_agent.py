"""Bear researcher for TradingAgents-style debate."""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult


class BearResearcherAgent:
    agent_name = "bear_researcher"

    def argue(self, *, evidence_refs: list[str], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "memo_type": "bear_research_memo",
            "uses_only_evidence_refs": True,
            "evidence_refs": evidence_refs,
            "downside": context.get("downside", "Backtest or paper evidence may not survive cost and regime shifts."),
            "hidden_risks": context.get("hidden_risks", ["overfitting", "correlation", "execution_cost_drift"]),
            "overfitting_concerns": context.get("overfitting_concerns", "Reject isolated best parameters and require stable clusters."),
            "correlation_concerns": context.get("correlation_concerns", "Portfolio cluster exposure must remain below policy."),
            "recommendation": "require_synthesis_and_risk_gate",
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output=self.argue(evidence_refs=task_input.get("evidence_refs", []), context=task_input),
        )


__all__ = ["BearResearcherAgent"]

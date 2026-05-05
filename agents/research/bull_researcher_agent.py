"""Bull researcher for TradingAgents-style debate."""

from __future__ import annotations

from typing import Any

from agents.base import AgentRunContext, AgentRunResult


class BullResearcherAgent:
    agent_name = "bull_researcher"

    def argue(self, *, evidence_refs: list[str], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "memo_type": "bull_research_memo",
            "uses_only_evidence_refs": True,
            "evidence_refs": evidence_refs,
            "upside": context.get("upside", "Potential edge if robustness, risk, and paper evidence remain intact."),
            "favorable_market_regime": context.get("favorable_market_regime", "Ranging or transition regimes with controlled costs."),
            "portfolio_benefits": context.get("portfolio_benefits", "May diversify existing strategy cluster if correlation stays below policy."),
            "recommendation": "proceed_to_bear_review",
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output=self.argue(evidence_refs=task_input.get("evidence_refs", []), context=task_input),
        )


__all__ = ["BullResearcherAgent"]

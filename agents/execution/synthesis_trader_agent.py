"""Synthesis trader for debate outputs.

This agent recommends; it never places orders directly.
"""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult


class SynthesisTraderAgent:
    agent_name = "synthesis_trader"

    def synthesize(
        self,
        *,
        analyst_reports: list[dict[str, Any]],
        bull_memo: dict[str, Any],
        bear_memo: dict[str, Any],
        risk_governor_output: dict[str, Any],
    ) -> dict[str, Any]:
        risk_clear = risk_governor_output.get("decision") == "approved"
        recommendation = "paper_or_micro_live_candidate" if risk_clear else "reject_or_revise"
        return {
            "memo_type": "synthesis_trader_memo",
            "analyst_reports_reviewed": len(analyst_reports),
            "bull_memo": bull_memo,
            "bear_memo": bear_memo,
            "risk_governor_output": risk_governor_output,
            "recommendation": recommendation,
            "never_place_order_directly": True,
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output=self.synthesize(
                analyst_reports=task_input.get("analyst_reports", []),
                bull_memo=task_input.get("bull_memo", {}),
                bear_memo=task_input.get("bear_memo", {}),
                risk_governor_output=task_input.get("risk_governor_output", {}),
            ),
        )


__all__ = ["SynthesisTraderAgent"]

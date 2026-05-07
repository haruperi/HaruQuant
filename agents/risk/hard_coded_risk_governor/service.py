"""Compatibility wrapper for the deterministic RiskGovernor."""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult
from services.risk.governor import RiskGovernor


class HardCodedRiskGovernorAgent:
    agent_name = "hard_coded_risk_governor"

    def __init__(self, *, governor: RiskGovernor | None = None) -> None:
        self.governor = governor or RiskGovernor()

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        decision = self.governor.evaluate_trade(proposal=task_input.get("proposal", {}), portfolio_snapshot=task_input.get("portfolio_snapshot", {}), market_snapshot=task_input.get("market_snapshot", {}))
        return AgentRunResult(agent_name=self.agent_name, status="completed" if decision.decision in {"approved", "approved_with_reduced_size"} else "blocked", output=decision.__dict__)


__all__ = ["HardCodedRiskGovernorAgent"]


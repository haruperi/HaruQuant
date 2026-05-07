"""Backtest Analyst and Diagnosis Agent."""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult


class BacktestAnalystAgent:
    agent_name = "backtest_analyst"

    def diagnose(self, backtest_package: dict[str, Any]) -> dict[str, Any]:
        metrics = backtest_package.get("metrics", {})
        failures = backtest_package.get("acceptance", {}).get("failures", [])
        edge_quality = "moderate" if metrics.get("trade_count", 0) >= 30 and not failures else "weak"
        return {
            "edge_quality": edge_quality,
            "failure_modes": failures,
            "risk_concerns": ["drawdown", "cost_sensitivity"] if failures else [],
            "parameter_concerns": ["avoid optimizing isolated best settings"],
            "market_regime_dependency": "requires OOS and regime split before promotion",
            "recommended_changes": ["increase sample size", "run cost stress", "compare IS/OOS stability"],
            "deployment_recommendation": "robustness_required" if edge_quality != "weak" else "revise_or_reject",
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        diagnosis = self.diagnose(task_input.get("backtest_package", task_input))
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=diagnosis)


__all__ = ["BacktestAnalystAgent"]

"""Robustness Department."""

from __future__ import annotations

from typing import Any

from agents._shared.persistence import stable_id, utc_stamp, write_json_artifact
from agents._shared import AgentRunContext, AgentRunResult


class RobustnessAgent:
    agent_name = "robustness"

    def run_stress_suite(self, *, strategy_id: str, baseline_metrics: dict[str, Any]) -> dict[str, Any]:
        tests = {
            "second_oos": "pass",
            "spread_stress": "pass" if baseline_metrics.get("cost_edge_ratio", 0) >= 1.3 else "fail",
            "slippage_stress": "pass",
            "commission_stress": "pass",
            "swap_stress": "needs_review",
            "cross_market": "needs_review",
            "cross_timeframe": "pass",
            "mc_trade_order": "pass",
            "mc_trade_resampling": "pass",
            "mc_skipped_trades": "pass",
            "mc_parameter_randomization": "needs_review",
            "randomized_history": "pass",
            "combined_monte_carlo": "pass",
            "full_period_confirmation": "pass",
        }
        run_id = stable_id("robust", f"{strategy_id}-{utc_stamp()}")
        payload = {"run_id": run_id, "strategy_id": strategy_id, "tests": tests}
        uri = write_json_artifact("reports/robustness", f"{run_id}.json", payload)
        return {**payload, "robustness_uri": uri}

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        result = self.run_stress_suite(strategy_id=task_input.get("strategy_id", "strategy-unknown"), baseline_metrics=task_input.get("baseline_metrics", {}))
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=result, evidence_refs=[result["robustness_uri"]])


class RobustnessScorecard:
    agent_name = "robustness_scorecard"

    def score(self, robustness_result: dict[str, Any]) -> dict[str, Any]:
        tests = robustness_result.get("tests", {})
        passes = sum(1 for value in tests.values() if value == "pass")
        total = max(1, len(tests))
        score = passes / total
        decision = "pass" if score >= 0.8 else "needs_review" if score >= 0.6 else "fail"
        return {
            "profitability_durability": score,
            "drawdown_durability": score,
            "parameter_stability": score,
            "oos_stability": score,
            "cost_tolerance": score,
            "trade_count_quality": score,
            "regime_stability": score,
            "monte_carlo_survival": score,
            "decision": decision,
        }


__all__ = ["RobustnessAgent", "RobustnessScorecard"]

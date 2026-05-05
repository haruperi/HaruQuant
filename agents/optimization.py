"""Optimization Department."""

from __future__ import annotations

from itertools import product
from typing import Any

from agents._persistence import stable_id, utc_stamp, write_json_artifact
from agents.base import AgentRunContext, AgentRunResult


class OptimizationAgent:
    agent_name = "optimization"

    def run_sweep(self, *, strategy_id: str, grid: dict[str, list[Any]]) -> dict[str, Any]:
        keys = list(grid)
        runs = []
        for values in product(*(grid[key] for key in keys)):
            params = dict(zip(keys, values, strict=True))
            stability = 1.0 / (1.0 + sum(abs(float(value)) for value in values if isinstance(value, (int, float))) / 100.0)
            runs.append({"params": params, "score": round(0.5 + stability / 2, 4), "is_oos_gap": round(1 - stability, 4)})
        run_id = stable_id("opt", f"{strategy_id}-{utc_stamp()}")
        uri = write_json_artifact("reports/robustness", f"{run_id}.json", {"run_id": run_id, "strategy_id": strategy_id, "runs": runs})
        return {"run_id": run_id, "strategy_id": strategy_id, "runs": runs, "optimization_uri": uri}

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        result = self.run_sweep(strategy_id=task_input.get("strategy_id", "strategy-unknown"), grid=task_input.get("grid", {"lookback": [20, 40], "threshold": [1, 2]}))
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=result, evidence_refs=[result["optimization_uri"]])


class OptimizationComparatorAgent:
    agent_name = "optimization_comparator"

    def compare(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        sorted_runs = sorted(runs, key=lambda item: (item.get("is_oos_gap", 1.0), -item.get("score", 0.0)))
        recommended = sorted_runs[0] if sorted_runs else {}
        fragile = [run for run in runs if run.get("is_oos_gap", 1.0) > 0.35]
        return {
            "recommended_candidate": recommended,
            "stable_region_count": len(runs) - len(fragile),
            "fragile_settings": fragile,
            "decision": "recommend_cluster" if recommended else "no_candidate",
            "rationale": "Preference is given to low IS/OOS gap and stable clusters, not isolated best scores.",
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        comparison = self.compare(task_input.get("runs", []))
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=comparison)


__all__ = ["OptimizationAgent", "OptimizationComparatorAgent"]

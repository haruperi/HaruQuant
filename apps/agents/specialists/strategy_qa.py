"""Deterministic strategy QA over stored validation artifacts."""

from __future__ import annotations

from typing import Any, Dict, List

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.tool_registry import ToolRegistry


class StrategyQAAgent:
    """Build a bounded promote/hold/reject memo from stored artifacts."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def run(self, task: AgentTask) -> AgentResult:
        """Review persisted validation artifacts and emit a deterministic memo."""
        backtest_id = int(task.input_payload.get("backtest_id") or 0)
        optimization_id = int(task.input_payload.get("optimization_id") or 0)
        strategy_version_id = int(task.input_payload.get("strategy_version_id") or 0)
        monte_carlo_id = task.input_payload.get("monte_carlo_id")

        backtest_run = self.tool_registry.execute("backtest_get_run", backtest_id=backtest_id)
        finance = self.tool_registry.execute("backtest_get_finance_metrics", backtest_id=backtest_id)
        optimization_run = self.tool_registry.execute(
            "optimization_get_run",
            optimization_id=optimization_id,
        )
        top_results = self.tool_registry.execute(
            "optimization_get_top_results",
            optimization_id=optimization_id,
            limit=3,
        )
        wfo_summary = self.tool_registry.execute(
            "validation_get_wfo_summary",
            optimization_id=optimization_id,
        )
        manifest = self.tool_registry.execute(
            "validation_get_manifest",
            strategy_version_id=strategy_version_id,
        )
        mc_summary = None
        if monte_carlo_id is not None:
            mc_summary = self.tool_registry.execute(
                "validation_get_monte_carlo_summary",
                simulation_id=int(monte_carlo_id),
            )

        status, reasons = self._classify(backtest_run, finance, wfo_summary, mc_summary)
        summary = (
            f"Strategy QA for backtest {backtest_id}: {status}. "
            f"Profit factor={finance.get('summary', {}).get('profit_factor')}, "
            f"sharpe={finance.get('summary', {}).get('sharpe_ratio')}, "
            f"WFO consistency={None if wfo_summary is None else wfo_summary.get('consistency_score')}."
        )
        evidence = [
            {"type": "backtest_run", "backtest_id": backtest_id},
            {"type": "optimization_run", "optimization_id": optimization_id},
            {"type": "strategy_manifest", "strategy_version_id": strategy_version_id},
        ]
        if monte_carlo_id is not None:
            evidence.append({"type": "monte_carlo", "simulation_id": int(monte_carlo_id)})

        recommendations: List[Dict[str, Any]] = [
            {"type": "qa_reason", "message": reason} for reason in reasons
        ]
        if top_results:
            recommendations.append(
                {
                    "type": "top_candidate",
                    "backtest_id": top_results[0].get("backtest_id"),
                    "score": top_results[0].get("score"),
                    "rank": top_results[0].get("rank"),
                }
            )

        return AgentResult(
            status="ok",
            summary=summary,
            evidence=evidence,
            recommendations=recommendations,
            required_actions=[],
            warnings=[],
            confidence=0.78,
            metadata={
                "workflow": "strategy_promotion_review",
                "decision": status,
                "optimization_status": None if optimization_run is None else optimization_run.get("status"),
                "manifest_present": manifest is not None,
            },
        )

    def _classify(
        self,
        backtest_run: Dict[str, Any] | None,
        finance: Dict[str, Any],
        wfo_summary: Dict[str, Any] | None,
        mc_summary: Dict[str, Any] | None,
    ) -> tuple[str, List[str]]:
        reasons: List[str] = []
        if backtest_run is None:
            return "reject", ["Backtest run is missing."]

        summary = dict(finance.get("summary") or {})
        profit_factor = float(summary.get("profit_factor") or 0.0)
        sharpe_ratio = float(summary.get("sharpe_ratio") or 0.0)
        win_rate = float(summary.get("win_rate") or 0.0)

        if profit_factor >= 1.5:
            reasons.append("Profit factor meets baseline threshold.")
        else:
            reasons.append("Profit factor is below the baseline threshold.")
        if sharpe_ratio >= 1.0:
            reasons.append("Sharpe ratio is acceptable.")
        else:
            reasons.append("Sharpe ratio is weak.")
        if win_rate >= 45.0:
            reasons.append("Win rate is reasonable.")
        else:
            reasons.append("Win rate is low.")

        if wfo_summary is not None:
            consistency = float(wfo_summary.get("consistency_score") or 0.0)
            if consistency >= 50.0:
                reasons.append("Walk-forward consistency is acceptable.")
            else:
                reasons.append("Walk-forward consistency is weak.")

        if mc_summary is not None:
            ruin = float(mc_summary.get("probability_of_ruin") or 0.0)
            if ruin <= 0.2:
                reasons.append("Monte Carlo ruin probability is acceptable.")
            else:
                reasons.append("Monte Carlo ruin probability is elevated.")

        if profit_factor >= 1.5 and sharpe_ratio >= 1.0:
            if wfo_summary is None or float(wfo_summary.get("consistency_score") or 0.0) >= 50.0:
                return "promote", reasons
        if profit_factor >= 1.2 and sharpe_ratio >= 0.5:
            return "hold", reasons
        return "reject", reasons

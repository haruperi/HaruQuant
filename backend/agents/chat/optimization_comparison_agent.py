"""Optimization comparison specialist for chat responses."""

from __future__ import annotations

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult


class OptimizationComparisonAgent:
    agent_name = "optimization_comparison_agent"

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        optimization = self._result(tool_results, "optimization_results")
        backtest = self._result(tool_results, "backtest_summary")
        if optimization is None and backtest is None:
            return None

        findings: list[str] = []
        evidence: list[str] = []

        if optimization is not None:
            payload = optimization.payload
            if payload.get("optimization_found"):
                evidence.extend(self._headline_metrics(payload.get("headline_metrics", {})))
                if payload.get("best_score") is not None:
                    findings.append(f"Best optimization score is {payload['best_score']}.")
                top_results = payload.get("top_results") or []
                if isinstance(top_results, list) and len(top_results) > 1:
                    first = top_results[0]
                    second = top_results[1]
                    findings.append(
                        "Top candidates differ on "
                        f"score={first.get('score')} vs {second.get('score')} and "
                        f"max_drawdown={first.get('max_drawdown')} vs {second.get('max_drawdown')}."
                    )

        if backtest is not None:
            payload = backtest.payload
            if payload.get("backtest_found"):
                evidence.append(f"backtest_id={payload.get('backtest_id')}")
                evidence.extend(self._headline_metrics(payload.get("headline_metrics", {})))

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary="Comparison specialist evidence is available and should anchor the answer on score, drawdown, Sharpe, and robustness tradeoffs.",
            findings=findings or ["Comparison should be grounded on optimization or backtest metrics that are currently available."],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation="Prefer the candidate with stronger return quality after checking whether the drawdown and score gap are actually material.",
            confidence=78 if optimization is not None else 69,
        )

    @staticmethod
    def _result(tool_results: list[ToolExecutionResult], tool_name: str) -> ToolExecutionResult | None:
        for result in tool_results:
            if result.tool_name == tool_name and result.success:
                return result
        return None

    @staticmethod
    def _headline_metrics(metrics: dict[str, object]) -> list[str]:
        if not isinstance(metrics, dict):
            return []
        return [f"{key}={value}" for key, value in list(metrics.items())[:5]]

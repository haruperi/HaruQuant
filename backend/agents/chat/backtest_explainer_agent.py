"""Backtest-focused chat specialist for diagnostics and strategy explanation."""

from __future__ import annotations

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult


class BacktestExplainerAgent:
    agent_name = "backtest_explainer_agent"

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        backtest = self._result(tool_results, "backtest_summary")
        strategy = self._result(tool_results, "strategy_parameters")
        if backtest is None and strategy is None:
            return None

        evidence: list[str] = []
        findings: list[str] = []

        if backtest is not None:
            payload = backtest.payload
            if payload.get("backtest_found"):
                evidence.extend(self._headline_metrics(payload.get("headline_metrics", {})))
                if payload.get("total_trades") is not None:
                    findings.append(f"Total trades in scope: {payload['total_trades']}.")
                if payload.get("timeframes"):
                    findings.append(f"Timeframes referenced: {payload['timeframes']}.")

        if strategy is not None:
            payload = strategy.payload
            if payload.get("strategy_found"):
                findings.append(
                    f"Strategy context is {payload.get('name') or payload.get('strategy_id')}, active version {payload.get('active_version') or 'unknown'}."
                )
                parameters = payload.get("parameters") or {}
                if isinstance(parameters, dict) and parameters:
                    sample = ", ".join(f"{key}={value}" for key, value in list(parameters.items())[:3])
                    evidence.append(f"strategy_parameters={sample}")

        if task_class == "diagnostic":
            summary = "Backtest and strategy evidence suggest the answer should focus on realized performance, trade activity, and parameter context."
            recommendation = "Inspect drawdown, trade count, and strategy-parameter changes before changing the hypothesis."
        else:
            summary = "Backtest evidence is available and can anchor the explanation in realized HaruQuant results."
            recommendation = "Use the backtest metrics as the primary evidence base for any follow-up explanation."

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary=summary,
            findings=findings or ["Backtest context is available for this request."],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation=recommendation,
            confidence=76 if backtest is not None else 68,
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

"""Backtest-focused chat specialist for diagnostics and strategy explanation."""

from __future__ import annotations

from typing import Any

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class BacktestExplainerAgent(SpecialistAgentBase):
    """LLM-backed backtest diagnostics specialist.

    Analyzes backtest metrics (Sharpe, drawdown, win rate, profit factor,
    trade count) and returns a structured diagnosis with grounded findings.
    Falls back to deterministic string-building if the LLM is unavailable.
    """

    agent_name = "backtest_explainer_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Backtest Diagnostics specialist.
Analyze the provided backtest metrics and produce a structured JSON diagnosis.

Output schema (JSON only):
{
  "summary": "<one sentence grounded in the metrics>",
  "findings": [
    "FACT: <neutral observation of a metric>",
    "INTERPRETATION: <what this fact implies for strategy performance>",
    "RISK: <a specific downside or edge case highlighted by this data>"
  ],
  "evidence": ["metric=value", ...],
  "recommendation": "<one concrete next action, e.g., 'reduce leverage', 'test on M30', 'check outlier trades'>",
  "confidence": <integer 0-100>,
  "missing_data": ["<metric name>", ...]
}

Rules:
- findings MUST follow the FACT/INTERPRETATION/RISK prefix pattern.
- FACTs must reference actual metric values provided.
- INTERPRETATION must be grounded in quantitative logic, not generic trading wisdom.
- RISK must be specific to the metrics (e.g., 'High kurtosis suggests fat-tail risk' instead of 'Trading is risky').
- if Sharpe ratio, max_drawdown, or profit_factor are absent, list them in missing_data.
- confidence must be < 70 if more than 2 critical metrics are missing.
- recommendation must name a specific metric, test, or workflow step.
- do not suggest live trades or broker actions.
- maximum 6 findings (2 sets of Fact/Interpretation/Risk).
"""

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        backtest = self._get_result(tool_results, "backtest_summary")
        strategy = self._get_result(tool_results, "strategy_parameters")

        if backtest is None and strategy is None:
            return None

        deterministic = self._deterministic_artifact(
            task_class=task_class,
            backtest=backtest,
            strategy=strategy,
            page_context=page_context,
        )

        user_payload = self._build_user_payload(
            backtest=backtest,
            strategy=strategy,
            task_class=task_class,
        )
        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)

    @staticmethod
    def _build_user_payload(
        *,
        backtest: ToolExecutionResult | None,
        strategy: ToolExecutionResult | None,
        task_class: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"task_class": task_class}

        if backtest is not None:
            b = backtest.payload
            headline = b.get("headline_metrics") or {}
            payload["backtest"] = {
                "backtest_id": b.get("backtest_id"),
                "total_trades": b.get("total_trades"),
                "timeframes": b.get("timeframes"),
                "headline_metrics": dict(list(headline.items())[:12]) if isinstance(headline, dict) else {},
            }

        if strategy is not None:
            s = strategy.payload
            parameters = s.get("parameters") or {}
            payload["strategy"] = {
                "name": s.get("name") or s.get("strategy_id"),
                "active_version": s.get("active_version"),
                "parameters": dict(list(parameters.items())[:6]) if isinstance(parameters, dict) else {},
            }

        return payload

    def _deterministic_artifact(
        self,
        *,
        task_class: str,
        backtest: ToolExecutionResult | None,
        strategy: ToolExecutionResult | None,
        page_context: Any,
    ) -> SpecialistAgentArtifact | None:
        evidence: list[str] = []
        findings: list[str] = []

        if backtest is not None:
            b = backtest.payload
            if b.get("backtest_found"):
                evidence.extend(self._headline_metrics(b.get("headline_metrics", {})))
                if b.get("total_trades") is not None:
                    findings.append(f"Total trades in scope: {b['total_trades']}.")
                if b.get("timeframes"):
                    findings.append(f"Timeframes referenced: {b['timeframes']}.")

        if strategy is not None:
            s = strategy.payload
            if s.get("strategy_found"):
                findings.append(
                    f"Strategy context is {s.get('name') or s.get('strategy_id')}, "
                    f"active version {s.get('active_version') or 'unknown'}."
                )
                parameters = s.get("parameters") or {}
                if isinstance(parameters, dict) and parameters:
                    sample = ", ".join(f"{k}={v}" for k, v in list(parameters.items())[:3])
                    evidence.append(f"strategy_parameters={sample}")

        if task_class == "diagnostic":
            summary = (
                "Backtest and strategy evidence suggest the answer should focus on "
                "realized performance, trade activity, and parameter context."
            )
            recommendation = (
                "Inspect drawdown, trade count, and strategy-parameter changes "
                "before changing the hypothesis."
            )
        else:
            summary = (
                "Backtest evidence is available and can anchor the explanation "
                "in realized HaruQuant results."
            )
            recommendation = (
                "Use the backtest metrics as the primary evidence base for "
                "any follow-up explanation."
            )

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary=summary,
            findings=findings or ["Backtest context is available for this request."],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation=recommendation,
            confidence=76 if backtest is not None else 68,
        )

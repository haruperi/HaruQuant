"""Optimization comparison specialist for chat responses."""

from __future__ import annotations

from typing import Any

from backend_retiring.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend_retiring.agents.chat.ai_chat.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class OptimizationComparisonAgent(SpecialistAgentBase):
    """LLM-backed optimization candidate selection specialist.

    Ranks top candidates by robustness-adjusted return quality rather than
    raw score. Returns a structured comparison grounded in the optimization
    result metrics. Falls back to deterministic string-building if the LLM
    is unavailable.
    """

    agent_name = "optimization_comparison_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Optimization Selection specialist.
Compare the top optimization candidates and produce a structured JSON ranking.

Output schema (JSON only):
{
  "summary": "<one sentence summarizing the comparison>",
  "findings": [
    "FACT: <neutral observation of a candidate metric or rank>",
    "INTERPRETATION: <what this fact implies for candidate quality>",
    "RISK: <a specific downside, e.g., overfitting, drawdown, or parameter sensitivity>"
  ],
  "evidence": ["key=value", ...],
  "recommendation": "<one concrete next action, e.g., 'backtest candidate #1 on different symbol', 'review candidate #2 parameters'>",
  "confidence": <integer 0-100>,
  "winner_index": <0 or 1>,
  "missing_data": ["<missing field>", ...]
}

Rules:
- findings MUST follow the FACT/INTERPRETATION/RISK prefix pattern.
- rank by robustness-adjusted return quality, not raw optimization score alone.
- if candidates differ by less than 5 percent on Sharpe or profit_factor, call it a tie in findings.
- if the top candidate has max_drawdown > 25 percent, add a drawdown warning in a RISK finding.
- winner_index must be 0 or 1 (index into the top_results list).
- if only one candidate is present, set winner_index to 0.
- if top_results is absent or empty, set missing_data to ["top_results"] and confidence to 0.
- do not suggest live trades or broker actions.
- maximum 6 findings (2 sets of Fact/Interpretation/Risk).
"""

    _REQUIRED_KEYS = ("summary", "findings", "evidence", "recommendation", "confidence", "winner_index")

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        optimization = self._get_result(tool_results, "optimization_results")
        backtest = self._get_result(tool_results, "backtest_summary")

        if optimization is None and backtest is None:
            return None

        deterministic = self._deterministic_artifact(
            task_class=task_class,
            optimization=optimization,
            backtest=backtest,
            page_context=page_context,
        )

        user_payload = self._build_user_payload(
            optimization=optimization,
            backtest=backtest,
            task_class=task_class,
        )
        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)

    def _extra_validate(self, raw: dict[str, Any]) -> bool:
        """Ensure winner_index is 0 or 1."""
        winner = raw.get("winner_index")
        return isinstance(winner, int) and winner in {0, 1}

    @staticmethod
    def _build_user_payload(
        *,
        optimization: ToolExecutionResult | None,
        backtest: ToolExecutionResult | None,
        task_class: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"task_class": task_class}

        if optimization is not None:
            o = optimization.payload
            top_results = o.get("top_results") or []
            headline = o.get("headline_metrics") or {}
            payload["optimization"] = {
                "optimization_id": o.get("optimization_id"),
                "best_score": o.get("best_score"),
                "headline_metrics": dict(list(headline.items())[:8]) if isinstance(headline, dict) else {},
                "top_results": [
                    {
                        "score": r.get("score"),
                        "sharpe": r.get("sharpe"),
                        "profit_factor": r.get("profit_factor"),
                        "max_drawdown": r.get("max_drawdown"),
                        "total_trades": r.get("total_trades"),
                        "net_profit": r.get("net_profit"),
                        "parameters": r.get("parameters"),
                    }
                    for r in (top_results[:3] if isinstance(top_results, list) else [])
                ],
            }

        if backtest is not None:
            b = backtest.payload
            headline = b.get("headline_metrics") or {}
            payload["backtest"] = {
                "backtest_id": b.get("backtest_id"),
                "headline_metrics": dict(list(headline.items())[:6]) if isinstance(headline, dict) else {},
            }

        return payload

    def _deterministic_artifact(
        self,
        *,
        task_class: str,
        optimization: ToolExecutionResult | None,
        backtest: ToolExecutionResult | None,
        page_context: Any,
    ) -> SpecialistAgentArtifact | None:
        findings: list[str] = []
        evidence: list[str] = []

        if optimization is not None:
            o = optimization.payload
            if o.get("optimization_found"):
                evidence.extend(self._headline_metrics(o.get("headline_metrics", {})))
                if o.get("best_score") is not None:
                    findings.append(f"Best optimization score is {o['best_score']}.")
                top_results = o.get("top_results") or []
                if isinstance(top_results, list) and len(top_results) > 1:
                    first = top_results[0]
                    second = top_results[1]
                    findings.append(
                        "Top candidates differ on "
                        f"score={first.get('score')} vs {second.get('score')} and "
                        f"max_drawdown={first.get('max_drawdown')} vs {second.get('max_drawdown')}."
                    )

        if backtest is not None:
            b = backtest.payload
            if b.get("backtest_found"):
                evidence.append(f"backtest_id={b.get('backtest_id')}")
                evidence.extend(self._headline_metrics(b.get("headline_metrics", {})))

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary=(
                "Comparison specialist evidence is available and should anchor the answer "
                "on score, drawdown, Sharpe, and robustness tradeoffs."
            ),
            findings=findings or [
                "Comparison should be grounded on optimization or backtest metrics that are currently available."
            ],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation=(
                "Prefer the candidate with stronger return quality after checking whether "
                "the drawdown and score gap are actually material."
            ),
            confidence=78 if optimization is not None else 69,
        )

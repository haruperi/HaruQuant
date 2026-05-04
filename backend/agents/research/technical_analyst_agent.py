"""Read-only Technical Analyst Agent."""

from __future__ import annotations

from typing import Any

from backend.agents.base import AgentRunContext, AgentRunResult, BaseAgent
from backend.agents.schemas import ResearchReport
from backend.agents.research.common import (
    close_prices,
    infer_trend,
    infer_volatility_regime,
    new_report_id,
    normalize_ohlcv,
    pct_returns,
    save_research_report,
    simple_rsi,
)


class TechnicalAnalystAgent(BaseAgent):
    agent_name = "technical_analyst"
    role = "Technical Analyst Agent"
    allowed_tools = ("get_symbol_data", "get_latest_ohlcv", "get_analytics_summary")

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        rows = normalize_ohlcv(task_input.get("ohlcv"))
        prices = close_prices(rows)
        returns = pct_returns(prices)
        trend = infer_trend(prices)
        volatility = infer_volatility_regime(returns)
        rsi = simple_rsi(prices)
        support = min(prices[-20:]) if len(prices) >= 20 else None
        resistance = max(prices[-20:]) if len(prices) >= 20 else None
        mean_reversion_score = _score_mean_reversion(trend, volatility, rsi)
        breakout_score = 0.75 if volatility in {"normal", "high"} and trend != "ranging" else 0.4
        trend_following_score = 0.8 if trend in {"trending_up", "trending_down"} else 0.35

        report = ResearchReport(
            report_id=new_report_id("technical-analysis"),
            research_question=str(task_input.get("research_question") or context.user_request or "Assess technical setup."),
            source_agent=self.agent_name,
            sources_used=["ohlcv"] if rows else [],
            market_context={
                "bars": len(rows),
                "trend": trend,
                "volatility": volatility,
                "rsi": rsi,
                "support": support,
                "resistance": resistance,
            },
            candidate_ideas=[
                {"idea": "mean_reversion", "score": mean_reversion_score, "rationale": "Uses RSI and range context."},
                {"idea": "breakout", "score": breakout_score, "rationale": "Uses trend and volatility expansion context."},
                {"idea": "trend_following", "score": trend_following_score, "rationale": "Uses directional context."},
            ],
            risks=["indicator_context_incomplete"] if rsi is None else [],
            recommended_next_steps=["Review candidate scores", "Promote only testable rules to Strategy Creator"],
            confidence=0.82 if len(rows) >= 30 else 0.4,
        )
        evidence = save_research_report(report)
        report = report.model_copy(update={"evidence_refs": [evidence]})
        return AgentRunResult(
            agent_name=self.agent_name,
            task_id=context.task_id,
            status="completed",
            output=report.model_dump(mode="json"),
            observations=({"observation_type": "technical_context", "summary": f"RSI={rsi}, trend={trend}."},),
            evidence_refs=(evidence.evidence_id,),
        )


def _score_mean_reversion(trend: str, volatility: str, rsi: float | None) -> float:
    score = 0.45
    if trend == "ranging":
        score += 0.25
    if volatility in {"normal", "low"}:
        score += 0.1
    if rsi is not None and (rsi < 35 or rsi > 65):
        score += 0.15
    return min(score, 1.0)


__all__ = ["TechnicalAnalystAgent"]

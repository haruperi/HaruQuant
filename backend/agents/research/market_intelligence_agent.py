"""Read-only Market Intelligence Agent."""

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
)


class MarketIntelligenceAgent(BaseAgent):
    agent_name = "market_intelligence"
    role = "Market Intelligence Agent"
    allowed_tools = ("get_symbol_data", "get_latest_ohlcv", "get_analytics_summary")

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        rows = normalize_ohlcv(task_input.get("ohlcv"))
        prices = close_prices(rows)
        returns = pct_returns(prices)
        trend = infer_trend(prices)
        volatility = infer_volatility_regime(returns)
        spreads = task_input.get("spreads") or []
        sessions = task_input.get("sessions") or []
        avg_spread = None
        if isinstance(spreads, list) and spreads:
            numeric_spreads = [float(value) for value in spreads if isinstance(value, (int, float))]
            avg_spread = sum(numeric_spreads) / len(numeric_spreads) if numeric_spreads else None

        report = ResearchReport(
            report_id=new_report_id("market-intelligence"),
            research_question=str(task_input.get("research_question") or context.user_request or "Assess market context."),
            source_agent=self.agent_name,
            sources_used=["ohlcv"] if rows else [],
            market_context={
                "bars": len(rows),
                "trend_regime": trend,
                "volatility_regime": volatility,
                "average_spread": avg_spread,
                "sessions_observed": sessions,
            },
            candidate_ideas=[
                {
                    "idea": "mean_reversion",
                    "rationale": "Ranging regime is more suitable for mean reversion.",
                    "score": 0.75 if trend == "ranging" else 0.35,
                },
                {
                    "idea": "trend_following",
                    "rationale": "Directional regime is more suitable for trend following.",
                    "score": 0.75 if trend in {"trending_up", "trending_down"} else 0.4,
                },
            ],
            risks=["insufficient_market_data"] if len(rows) < 20 else [],
            recommended_next_steps=["Run technical analysis", "Create strategy spec only from supported regimes"],
            confidence=0.8 if len(rows) >= 20 else 0.35,
        )
        evidence = save_research_report(report)
        report = report.model_copy(update={"evidence_refs": [evidence]})
        return AgentRunResult(
            agent_name=self.agent_name,
            task_id=context.task_id,
            status="completed",
            output=report.model_dump(mode="json"),
            observations=({"observation_type": "market_context", "summary": f"Detected {trend} / {volatility} regime."},),
            evidence_refs=(evidence.evidence_id,),
        )


__all__ = ["MarketIntelligenceAgent"]

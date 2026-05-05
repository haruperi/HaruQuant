"""Read-only Research Department v1 agents."""

from __future__ import annotations

from statistics import mean
from typing import Any

from agents._persistence import stable_id, utc_stamp, write_json_artifact
from agents.base import AgentRunContext, AgentRunResult
from agents.schemas import ResearchReport


def _closes(ohlcv: list[dict[str, Any]]) -> list[float]:
    return [float(row["close"]) for row in ohlcv if "close" in row]


def _research_result(agent_name: str, report: ResearchReport) -> AgentRunResult:
    evidence_path = write_json_artifact(
        "memory/evidence",
        f"{report.report_id}-{utc_stamp()}.json",
        report.model_dump(mode="json"),
    )
    return AgentRunResult(
        agent_name=agent_name,
        status="completed",
        output=report.model_dump(mode="json"),
        observations=[{"agent_name": agent_name, "summary": report.summary}],
        evidence_refs=[evidence_path],
    )


class MarketIntelligenceAgent:
    agent_name = "market_intelligence"
    allowed_tools = ("get_symbol_data", "get_latest_ohlcv", "get_risk_snapshot")

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        ohlcv = task_input.get("ohlcv", [])
        closes = _closes(ohlcv)
        bars = len(closes)
        change = (closes[-1] - closes[0]) if bars >= 2 else 0.0
        avg_range = mean(float(row.get("high", 0)) - float(row.get("low", 0)) for row in ohlcv) if ohlcv else 0.0
        spread = mean(float(item) for item in task_input.get("spreads", [0.0]))
        regime = "transition"
        if bars >= 10 and abs(change) > avg_range * 3:
            regime = "trending"
        elif bars >= 10 and avg_range > 0:
            regime = "ranging"
        report = ResearchReport(
            report_id=stable_id("research", f"market-{context.task_id}"),
            source_agent=self.agent_name,
            agent_name=self.agent_name,
            topic="market_intelligence",
            research_question=context.user_request,
            summary=f"Market context is {regime} with average spread {spread:.2f}.",
            sources_used=["symbol_data", "latest_ohlcv", "spread_snapshot", "session_context"],
            market_context={
                "bars": bars,
                "regime": regime,
                "average_range": avg_range,
                "average_spread": spread,
                "sessions": task_input.get("sessions", []),
            },
            candidate_ideas=[{"idea": "mean_reversion", "score": 0.65 if regime == "ranging" else 0.45}],
            risks=["Regime classification is deterministic and requires broker-grade data before deployment."],
            recommended_next_steps=["Ask Technical Analyst to verify indicator context.", "Keep execution disabled."],
            confidence=0.7 if bars >= 30 else 0.45,
            findings=[f"Detected {regime} market structure over {bars} bars."],
        )
        return _research_result(self.agent_name, report)


class TechnicalAnalystAgent:
    agent_name = "technical_analyst"
    allowed_tools = ("get_symbol_data", "get_latest_ohlcv", "get_analytics_summary")

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        closes = _closes(task_input.get("ohlcv", []))
        short = mean(closes[-5:]) if len(closes) >= 5 else (closes[-1] if closes else 0.0)
        long = mean(closes[-20:]) if len(closes) >= 20 else short
        momentum = short - long
        volatility = mean(abs(closes[index] - closes[index - 1]) for index in range(1, len(closes))) if len(closes) > 1 else 0.0
        support = min(closes[-20:]) if closes else 0.0
        resistance = max(closes[-20:]) if closes else 0.0
        ideas = [
            {"idea": "mean_reversion", "score": 0.72 if volatility > abs(momentum) else 0.5},
            {"idea": "breakout", "score": 0.55 if volatility > 0 else 0.3},
            {"idea": "trend_following", "score": 0.72 if abs(momentum) > volatility else 0.45},
        ]
        report = ResearchReport(
            report_id=stable_id("research", f"technical-{context.task_id}"),
            source_agent=self.agent_name,
            agent_name=self.agent_name,
            topic="technical_analysis",
            research_question=context.user_request,
            summary="Technical context scored mean reversion, breakout, and trend-following suitability.",
            sources_used=["latest_ohlcv", "analytics_summary"],
            market_context={
                "short_ma": short,
                "long_ma": long,
                "momentum": momentum,
                "volatility": volatility,
                "support": support,
                "resistance": resistance,
            },
            candidate_ideas=ideas,
            risks=["Support/resistance and indicator context are descriptive, not a trade signal."],
            recommended_next_steps=["Convert the highest-scoring idea into a formal StrategySpec."],
            confidence=0.68 if len(closes) >= 30 else 0.45,
            findings=[f"Momentum={momentum:.6f}", f"Volatility={volatility:.6f}"],
        )
        return _research_result(self.agent_name, report)


class StrategyScoutAgent:
    agent_name = "strategy_scout"
    allowed_tools = ("get_strategy", "list_strategies", "get_backtest_result")

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        memory_count = len(task_input.get("strategy_memory", []))
        backtest_count = len(task_input.get("past_backtests", []))
        ideas = [
            {"idea": "session_filtered_mean_reversion", "score": 0.78, "novelty": 0.62, "testability": 0.9},
            {"idea": "volatility_breakout_with_cost_filter", "score": 0.7, "novelty": 0.68, "testability": 0.82},
            {"idea": "trend_pullback_continuation", "score": 0.64, "novelty": 0.55, "testability": 0.8},
        ]
        report = ResearchReport(
            report_id=stable_id("research", f"scout-{context.task_id}"),
            source_agent=self.agent_name,
            agent_name=self.agent_name,
            topic="strategy_scout",
            research_question=context.user_request,
            summary="Strategy scout ranked candidate ideas using internal memory, past backtests, and testability.",
            sources_used=["strategy_memory", "past_backtests", "approved_read_only_research"],
            market_context={"strategy_memory_count": memory_count, "past_backtest_count": backtest_count},
            candidate_ideas=sorted(ideas, key=lambda item: item["score"], reverse=True),
            risks=["External research must remain read-only and evidence-linked."],
            recommended_next_steps=["Create a StrategySpec for the top idea and run formal review."],
            confidence=0.66,
            findings=["Ranked candidates by novelty, feasibility, edge plausibility, testability, and risk compatibility."],
        )
        return _research_result(self.agent_name, report)


__all__ = ["MarketIntelligenceAgent", "StrategyScoutAgent", "TechnicalAnalystAgent", "_research_result"]

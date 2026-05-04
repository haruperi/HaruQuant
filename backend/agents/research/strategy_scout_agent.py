"""Read-only Strategy Scout Agent."""

from __future__ import annotations

from typing import Any

from backend.agents.base import AgentRunContext, AgentRunResult, BaseAgent
from backend.agents.schemas import ResearchReport
from backend.agents.research.common import new_report_id, save_research_report


class StrategyScoutAgent(BaseAgent):
    agent_name = "strategy_scout"
    role = "Strategy Scout Agent"
    allowed_tools = ("get_strategy", "list_strategies", "get_backtest_result", "get_analytics_summary")

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        memory = task_input.get("strategy_memory") if isinstance(task_input.get("strategy_memory"), list) else []
        rejected = task_input.get("rejected_strategies") if isinstance(task_input.get("rejected_strategies"), list) else []
        past_backtests = task_input.get("past_backtests") if isinstance(task_input.get("past_backtests"), list) else []
        ideas = _candidate_ideas(memory=memory, rejected=rejected, past_backtests=past_backtests)
        report = ResearchReport(
            report_id=new_report_id("strategy-scout"),
            research_question=str(task_input.get("research_question") or context.user_request or "Find strategy ideas."),
            source_agent=self.agent_name,
            sources_used=["strategy_memory", "past_backtests", "rejected_strategies"],
            market_context={"memory_items": len(memory), "past_backtests": len(past_backtests), "rejected": len(rejected)},
            candidate_ideas=ideas,
            risks=["no_internal_memory_available"] if not memory and not past_backtests else [],
            recommended_next_steps=["Send top idea to Strategy Creator", "Reject low testability ideas"],
            confidence=0.76 if ideas else 0.3,
        )
        evidence = save_research_report(report)
        report = report.model_copy(update={"evidence_refs": [evidence]})
        return AgentRunResult(
            agent_name=self.agent_name,
            task_id=context.task_id,
            status="completed",
            output=report.model_dump(mode="json"),
            observations=({"observation_type": "strategy_scouting", "summary": f"Scored {len(ideas)} candidate ideas."},),
            evidence_refs=(evidence.evidence_id,),
        )


def _candidate_ideas(*, memory: list[Any], rejected: list[Any], past_backtests: list[Any]) -> list[dict[str, Any]]:
    rejected_names = {str(item.get("name") or item.get("strategy_name")) for item in rejected if isinstance(item, dict)}
    seeds = [
        ("EURUSD H1 RSI mean reversion", "mean_reversion"),
        ("London session breakout filter", "breakout"),
        ("Volatility regime trend continuation", "trend_following"),
    ]
    ideas: list[dict[str, Any]] = []
    for name, style in seeds:
        novelty = 0.5 if name in rejected_names else 0.8
        feasibility = 0.85 if style != "breakout" else 0.7
        edge = 0.65
        testability = 0.9
        risk = 0.75 if style == "mean_reversion" else 0.65
        score = round((novelty + feasibility + edge + testability + risk) / 5, 3)
        ideas.append(
            {
                "idea": name,
                "style": style,
                "novelty": novelty,
                "feasibility": feasibility,
                "edge_plausibility": edge,
                "testability": testability,
                "risk_compatibility": risk,
                "score": score,
            }
        )
    return sorted(ideas, key=lambda item: item["score"], reverse=True)


__all__ = ["StrategyScoutAgent"]

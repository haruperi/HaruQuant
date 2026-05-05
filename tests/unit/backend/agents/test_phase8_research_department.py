from __future__ import annotations

from agents.agent_registry import AgentRegistry
from agents.base import AgentRunContext
from agents.planner import PlannerAgent
from agents.research import MarketIntelligenceAgent, StrategyScoutAgent, TechnicalAnalystAgent
from agents.schemas import ResearchReport


def _sample_ohlcv() -> list[dict[str, float]]:
    rows = []
    price = 1.1000
    for index in range(40):
        price += 0.0002 if index < 20 else -0.0001
        rows.append(
            {
                "open": price - 0.0001,
                "high": price + 0.0005,
                "low": price - 0.0005,
                "close": price,
            }
        )
    return rows


def _context(agent_name: str = "research") -> AgentRunContext:
    return AgentRunContext(
        workflow_id="wf-research",
        task_id=f"task-{agent_name}",
        user_request="Research EURUSD H1 mean reversion context.",
    )


def test_market_intelligence_agent_outputs_research_report() -> None:
    result = MarketIntelligenceAgent().run(
        context=_context("market"),
        task_input={"ohlcv": _sample_ohlcv(), "spreads": [0.8, 1.0, 1.2], "sessions": ["London", "New York"]},
    )

    report = ResearchReport.model_validate(result.output)

    assert result.status == "completed"
    assert report.source_agent == "market_intelligence"
    assert report.market_context["bars"] == 40
    assert result.evidence_refs


def test_technical_analyst_agent_scores_strategy_suitability() -> None:
    result = TechnicalAnalystAgent().run(
        context=_context("technical"),
        task_input={"ohlcv": _sample_ohlcv()},
    )

    report = ResearchReport.model_validate(result.output)

    assert report.source_agent == "technical_analyst"
    assert {idea["idea"] for idea in report.candidate_ideas} == {
        "mean_reversion",
        "breakout",
        "trend_following",
    }


def test_strategy_scout_agent_outputs_ranked_ideas() -> None:
    result = StrategyScoutAgent().run(
        context=_context("scout"),
        task_input={"strategy_memory": [{"name": "old idea"}], "past_backtests": [{"id": "bt-1"}]},
    )

    report = ResearchReport.model_validate(result.output)

    assert report.source_agent == "strategy_scout"
    assert report.candidate_ideas[0]["score"] >= report.candidate_ideas[-1]["score"]


def test_research_agents_are_registered_read_only() -> None:
    registry = AgentRegistry()

    for agent_name in ("market_intelligence", "technical_analyst", "strategy_scout"):
        descriptor = registry.require(agent_name)
        assert "place_live_order" not in descriptor.allowed_tools
        assert "save_strategy_code" not in descriptor.allowed_tools


def test_planner_research_route_uses_research_department_v1_agents() -> None:
    plan = PlannerAgent().create_plan(user_request="Research EURUSD market structure")

    assert plan.intent == "research"
    assert plan.allowed_agents[:3] == [
        "market_intelligence",
        "technical_analyst",
        "strategy_scout",
    ]

from __future__ import annotations

from agents.research.shared.capabilities import AGENT_CAPABILITIES
from agents.research.shared.scoring import ResearchScorecard, calculate_research_score


def test_all_research_agents_have_capability_manifest():
    required_agents = {
        "research_orchestrator_agent",
        "market_intelligence_agent",
        "technical_analyst_agent",
        "strategy_scout_agent",
        "news_sentiment_agent",
        "macro_fundamental_context_agent",
        "cross_asset_intermarket_agent",
        "seasonality_calendar_agent",
        "strategy_hypothesis_agent",
        "research_validation_agent",
        "evidence_curator_agent",
    }

    assert required_agents <= set(AGENT_CAPABILITIES)
    for capabilities in AGENT_CAPABILITIES.values():
        assert capabilities.inputs
        assert capabilities.evidence_required
        assert capabilities.llm_responsibilities
        assert capabilities.deterministic_rules
        assert capabilities.output_artifacts
        assert capabilities.functional_capabilities
        assert capabilities.tests_required
        assert capabilities.traceable_claims


def test_research_score_is_weighted_and_normalized():
    score = calculate_research_score(
        ResearchScorecard(
            novelty_score=1.0,
            feasibility_score=1.0,
            edge_plausibility_score=1.0,
            testability_score=1.0,
            risk_compatibility_score=1.0,
            portfolio_fit_score=1.0,
            execution_realism_score=1.0,
            overfitting_risk_score=0.0,
            complexity_score=0.0,
        )
    )

    assert 0.0 <= score <= 1.0
    assert score == 1.0

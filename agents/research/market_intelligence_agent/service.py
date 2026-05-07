"""Service interface for the Market Intelligence Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="market_intelligence_agent",
    display_name="Market Intelligence Agent",
    report_type="market_intelligence_report",
    prompt_version="market_intelligence_agent_prompt_v1",
    policy_version="market_intelligence_agent_policy_v1",
    purpose='Studies market regimes, liquidity, volatility, session behavior, spread behavior, and symbol personality.',
    allowed_actions=('summarize_market_context', 'classify_market_regime', 'flag_spread_risk', 'flag_volatility_risk', 'flag_liquidity_risk', 'recommend_research_strategy_families', 'save_market_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('get_ohlcv_data', 'get_tick_data', 'get_spread_history', 'get_session_calendar', 'get_volatility_regime_history', 'get_symbol_metadata', 'save_market_intelligence_report'),
    required_evidence_sources=("ohlcv_history",),
    controlled_write_actions=('save_market_report',),
)


class MarketIntelligenceAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

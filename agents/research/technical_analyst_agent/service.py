"""Service interface for the Technical Analyst Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="technical_analyst_agent",
    display_name="Technical Analyst Agent",
    report_type="technical_analysis_report",
    prompt_version="technical_analyst_agent_prompt_v1",
    policy_version="technical_analyst_agent_policy_v1",
    purpose='Analyzes price structure, indicators, trend, momentum, volatility, support, and resistance.',
    allowed_actions=('analyze_price_structure', 'classify_trend_state', 'summarize_indicators', 'flag_technical_risks', 'save_technical_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('get_ohlcv_data', 'calculate_indicators', 'detect_support_resistance', 'detect_price_patterns', 'save_technical_analysis_report'),
    required_evidence_sources=("technical_context",),
    controlled_write_actions=('save_technical_report',),
)


class TechnicalAnalystAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

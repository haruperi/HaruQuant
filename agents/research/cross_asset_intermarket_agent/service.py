"""Service interface for the Cross-Asset / Intermarket Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="cross_asset_intermarket_agent",
    display_name="Cross-Asset / Intermarket Agent",
    report_type="cross_asset_intermarket_report",
    prompt_version="cross_asset_intermarket_agent_prompt_v1",
    policy_version="cross_asset_intermarket_agent_policy_v1",
    purpose='Analyzes related markets, correlations, divergences, intermarket pressure, and exposure context.',
    allowed_actions=('analyze_cross_asset_context', 'flag_correlation_shift', 'flag_intermarket_divergence', 'save_intermarket_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('get_cross_asset_data', 'calculate_correlations', 'detect_intermarket_divergence', 'save_cross_asset_report'),
    required_evidence_sources=("cross_asset_context",),
    controlled_write_actions=('save_intermarket_report',),
)


class CrossAssetIntermarketAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

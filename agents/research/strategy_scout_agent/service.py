"""Service interface for the Strategy Scout Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="strategy_scout_agent",
    display_name="Strategy Scout Agent",
    report_type="strategy_scout_report",
    prompt_version="strategy_scout_agent_prompt_v1",
    policy_version="strategy_scout_agent_policy_v1",
    purpose='Discovers candidate strategy ideas from market, technical, historical, and evidence-memory context.',
    allowed_actions=('discover_strategy_ideas', 'rank_candidate_ideas', 'reject_weak_ideas', 'save_strategy_idea_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('search_strategy_memory', 'retrieve_market_reports', 'retrieve_technical_reports', 'score_strategy_ideas', 'save_strategy_scout_report'),
    required_evidence_sources=("strategy_memory",),
    controlled_write_actions=('save_strategy_idea_report',),
)


class StrategyScoutAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

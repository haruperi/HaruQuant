"""Service interface for the Macro and Fundamental Context Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="macro_fundamental_context_agent",
    display_name="Macro and Fundamental Context Agent",
    report_type="macro_fundamental_report",
    prompt_version="macro_fundamental_context_agent_prompt_v1",
    policy_version="macro_fundamental_context_agent_policy_v1",
    purpose='Analyzes macro, fundamental, central-bank, rate, inflation, growth, and event context.',
    allowed_actions=('summarize_macro_context', 'classify_macro_regime', 'flag_macro_event_risk', 'save_macro_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('get_macro_calendar', 'get_fundamental_snapshot', 'get_rate_policy_context', 'save_macro_fundamental_report'),
    required_evidence_sources=("macro_context",),
    controlled_write_actions=('save_macro_report',),
)


class MacroFundamentalContextAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

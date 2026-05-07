"""Service interface for the Seasonality and Calendar Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="seasonality_calendar_agent",
    display_name="Seasonality and Calendar Agent",
    report_type="seasonality_calendar_report",
    prompt_version="seasonality_calendar_agent_prompt_v1",
    policy_version="seasonality_calendar_agent_policy_v1",
    purpose='Analyzes session, calendar, day-of-week, month-end, holiday, and seasonal behavior.',
    allowed_actions=('analyze_seasonality', 'flag_calendar_risk', 'summarize_session_patterns', 'save_seasonality_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('get_session_calendar', 'get_holiday_calendar', 'calculate_seasonality_profile', 'save_seasonality_calendar_report'),
    required_evidence_sources=("seasonality_context",),
    controlled_write_actions=('save_seasonality_report',),
)


class SeasonalityCalendarAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

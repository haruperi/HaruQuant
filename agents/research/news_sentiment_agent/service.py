"""Service interface for the News and Sentiment Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="news_sentiment_agent",
    display_name="News and Sentiment Agent",
    report_type="news_sentiment_report",
    prompt_version="news_sentiment_agent_prompt_v1",
    policy_version="news_sentiment_agent_policy_v1",
    purpose='Analyzes approved news and sentiment sources and flags event or narrative risk.',
    allowed_actions=('summarize_news_context', 'classify_sentiment', 'flag_news_risk', 'save_sentiment_report'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('get_approved_news_feed', 'get_sentiment_snapshot', 'get_economic_calendar', 'save_news_sentiment_report'),
    required_evidence_sources=("news_sentiment_snapshot",),
    controlled_write_actions=('save_sentiment_report',),
)


class NewsSentimentAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

"""Service interface for the Strategy Hypothesis Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="strategy_hypothesis_agent",
    display_name="Strategy Hypothesis Agent",
    report_type="strategy_hypothesis_report",
    prompt_version="strategy_hypothesis_agent_prompt_v1",
    policy_version="strategy_hypothesis_agent_policy_v1",
    purpose='Converts vetted research ideas into testable strategy hypotheses with acceptance and rejection criteria.',
    allowed_actions=('create_strategy_hypothesis', 'define_acceptance_criteria', 'define_rejection_criteria', 'save_strategy_hypothesis'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('retrieve_candidate_ideas', 'build_hypothesis_contract', 'save_strategy_hypothesis_report'),
    required_evidence_sources=("candidate_strategy_idea",),
    controlled_write_actions=('save_strategy_hypothesis',),
)


class StrategyHypothesisAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

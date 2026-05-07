"""Service interface for the Strategy Reviewer Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_reviewer_agent",
    display_name="Strategy Reviewer Agent",
    artifact_type="strategy_review_report",
    prompt_version="strategy_reviewer_agent_prompt_v1",
    policy_version="strategy_reviewer_agent_policy_v1",
    allowed_actions=('review_strategy_package', 'approve_for_backtesting', 'reject_unsafe_code', 'produce_fix_list'),
    tool_names=('read_strategy_spec', 'read_generated_code_package', 'run_static_strategy_review'),
    permission_profile="strategy_review_read_only_v1",
)


class StrategyReviewerAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

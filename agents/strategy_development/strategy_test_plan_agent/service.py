"""Service interface for the Strategy Test Plan Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_test_plan_agent",
    display_name="Strategy Test Plan Agent",
    artifact_type="strategy_test_plan",
    prompt_version="strategy_test_plan_agent_prompt_v1",
    policy_version="strategy_test_plan_agent_policy_v1",
    allowed_actions=('create_test_plan', 'create_robustness_plan', 'define_no_lookahead_tests'),
    tool_names=('read_strategy_spec', 'read_strategy_test_standards'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategyTestPlanAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

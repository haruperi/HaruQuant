"""Service interface for the Strategy Handoff Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_handoff_agent",
    display_name="Strategy Handoff Agent",
    artifact_type="strategy_validation_handoff_package",
    prompt_version="strategy_handoff_agent_prompt_v1",
    policy_version="strategy_handoff_agent_policy_v1",
    allowed_actions=('create_backtesting_handoff', 'validate_handoff_readiness', 'package_strategy_for_validation'),
    tool_names=('read_approved_strategy_package', 'write_validation_handoff'),
    permission_profile="strategy_handoff_write_v1",
)


class StrategyHandoffAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

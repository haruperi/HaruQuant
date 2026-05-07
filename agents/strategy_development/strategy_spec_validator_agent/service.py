"""Service interface for the Strategy Spec Validator Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_spec_validator_agent",
    display_name="Strategy Spec Validator Agent",
    artifact_type="strategy_spec_validation_report",
    prompt_version="strategy_spec_validator_agent_prompt_v1",
    policy_version="strategy_spec_validator_agent_policy_v1",
    allowed_actions=('validate_strategy_spec', 'reject_incomplete_spec', 'approve_spec_for_codegen'),
    tool_names=('read_strategy_spec', 'validate_strategy_template_rules'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategySpecValidatorAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

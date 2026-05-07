"""Service interface for the Strategy Rule Normalizer Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_rule_normalizer_agent",
    display_name="Strategy Rule Normalizer Agent",
    artifact_type="strategy_rule_normalization_report",
    prompt_version="strategy_rule_normalizer_agent_prompt_v1",
    policy_version="strategy_rule_normalizer_agent_policy_v1",
    allowed_actions=('normalize_strategy_rules', 'remove_vague_rules', 'produce_testable_rules'),
    tool_names=('read_strategy_spec', 'normalize_rule_text'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategyRuleNormalizerAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

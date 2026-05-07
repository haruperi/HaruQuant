"""Service interface for the Strategy Template Selector Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_template_selector_agent",
    display_name="Strategy Template Selector Agent",
    artifact_type="strategy_template_selection_report",
    prompt_version="strategy_template_selector_agent_prompt_v1",
    policy_version="strategy_template_selector_agent_policy_v1",
    allowed_actions=('select_strategy_template', 'select_base_classes', 'select_lifecycle_methods'),
    tool_names=('read_strategy_spec', 'read_template_rules'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategyTemplateSelectorAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

"""Service interface for the Strategy Spec Storage Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_spec_storage_agent",
    display_name="Strategy Spec Storage Agent",
    artifact_type="strategy_spec_storage_receipt",
    prompt_version="strategy_spec_storage_agent_prompt_v1",
    policy_version="strategy_spec_storage_agent_policy_v1",
    allowed_actions=('save_strategy_spec', 'version_strategy_spec', 'link_spec_lineage'),
    tool_names=('read_strategy_spec', 'write_strategy_memory'),
    permission_profile="strategy_spec_write_v1",
)


class StrategySpecStorageAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

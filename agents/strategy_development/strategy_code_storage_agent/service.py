"""Service interface for the Strategy Code Storage Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_code_storage_agent",
    display_name="Strategy Code Storage Agent",
    artifact_type="strategy_code_storage_receipt",
    prompt_version="strategy_code_storage_agent_prompt_v1",
    policy_version="strategy_code_storage_agent_policy_v1",
    allowed_actions=('save_strategy_code_package', 'version_code_package', 'link_code_lineage'),
    tool_names=('read_strategy_code_package', 'write_strategy_code_memory'),
    permission_profile="strategy_codegen_write_v1",
)


class StrategyCodeStorageAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

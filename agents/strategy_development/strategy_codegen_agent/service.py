"""Service interface for the Strategy Codegen Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_codegen_agent",
    display_name="Strategy Codegen Agent",
    artifact_type="strategy_code_package",
    prompt_version="strategy_codegen_agent_prompt_v1",
    policy_version="strategy_codegen_agent_policy_v1",
    allowed_actions=('generate_strategy_code_package', 'generate_strategy_tests', 'generate_strategy_readme', 'mark_generated_pending_review'),
    tool_names=('read_approved_strategy_spec', 'write_generated_code_artifacts'),
    permission_profile="strategy_codegen_write_v1",
)


class StrategyCodegenAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

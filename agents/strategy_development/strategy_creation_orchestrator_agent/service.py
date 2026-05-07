"""Service interface for the Strategy Creation Orchestrator Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_creation_orchestrator_agent",
    display_name="Strategy Creation Orchestrator Agent",
    artifact_type="strategy_creation_package",
    prompt_version="strategy_creation_orchestrator_agent_prompt_v1",
    policy_version="strategy_creation_orchestrator_agent_policy_v1",
    allowed_actions=('coordinate_strategy_creation', 'route_strategy_creation_tasks', 'produce_strategy_creation_package', 'block_incomplete_handoff'),
    tool_names=('read_research_handoff', 'run_strategy_creation_agents', 'save_strategy_creation_package'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategyCreationOrchestratorAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

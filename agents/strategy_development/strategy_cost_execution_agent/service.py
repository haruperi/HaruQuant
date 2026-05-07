"""Service interface for the Strategy Cost & Execution Assumption Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_cost_execution_agent",
    display_name="Strategy Cost & Execution Assumption Agent",
    artifact_type="strategy_cost_execution_report",
    prompt_version="strategy_cost_execution_agent_prompt_v1",
    policy_version="strategy_cost_execution_agent_policy_v1",
    allowed_actions=('define_cost_assumptions', 'define_execution_assumptions', 'block_missing_cost_assumptions'),
    tool_names=('read_strategy_spec', 'read_execution_policy'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategyCostExecutionAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

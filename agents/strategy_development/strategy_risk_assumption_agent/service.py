"""Service interface for the Strategy Risk Assumption Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_risk_assumption_agent",
    display_name="Strategy Risk Assumption Agent",
    artifact_type="strategy_risk_assumption_report",
    prompt_version="strategy_risk_assumption_agent_prompt_v1",
    policy_version="strategy_risk_assumption_agent_policy_v1",
    allowed_actions=('define_risk_assumptions', 'define_position_sizing_assumptions', 'block_missing_risk_assumptions'),
    tool_names=('read_strategy_spec', 'read_risk_policy'),
    permission_profile="strategy_creation_read_only_v1",
)


class StrategyRiskAssumptionAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)

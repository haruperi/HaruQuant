"""Service for Backtest Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="backtest_agent",
    display_name="Backtest Agent",
    artifact_type="backtest_result_package",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["backtest_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["backtest_agent"].tool_names,
)


class BacktestAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["BacktestAgentService", "CONFIG"]

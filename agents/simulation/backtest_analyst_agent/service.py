"""Service for Backtest Analyst Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="backtest_analyst_agent",
    display_name="Backtest Analyst Agent",
    artifact_type="backtest_diagnosis_report",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["backtest_analyst_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["backtest_analyst_agent"].tool_names,
)


class BacktestAnalystAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["BacktestAnalystAgentService", "CONFIG"]

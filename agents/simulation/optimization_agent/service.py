"""Service for Optimization Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="optimization_agent",
    display_name="Optimization Agent",
    artifact_type="optimization_package",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["optimization_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["optimization_agent"].tool_names,
)


class OptimizationAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["OptimizationAgentService", "CONFIG"]

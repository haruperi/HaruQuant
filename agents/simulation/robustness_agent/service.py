"""Service for Robustness Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="robustness_agent",
    display_name="Robustness Agent",
    artifact_type="robustness_report",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["robustness_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["robustness_agent"].tool_names,
)


class RobustnessAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["RobustnessAgentService", "CONFIG"]

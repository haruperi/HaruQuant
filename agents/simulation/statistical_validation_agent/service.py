"""Service for Statistical Validation Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="statistical_validation_agent",
    display_name="Statistical Validation Agent",
    artifact_type="statistical_validation_report",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["statistical_validation_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["statistical_validation_agent"].tool_names,
)


class StatisticalValidationAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["StatisticalValidationAgentService", "CONFIG"]

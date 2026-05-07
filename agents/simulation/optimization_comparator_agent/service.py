"""Service for Optimization Comparator Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="optimization_comparator_agent",
    display_name="Optimization Comparator Agent",
    artifact_type="optimization_comparison",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["optimization_comparator_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["optimization_comparator_agent"].tool_names,
)


class OptimizationComparatorAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["OptimizationComparatorAgentService", "CONFIG"]

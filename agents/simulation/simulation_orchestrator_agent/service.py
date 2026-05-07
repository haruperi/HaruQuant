"""Service for Simulation Orchestrator."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="simulation_orchestrator_agent",
    display_name="Simulation Orchestrator",
    artifact_type="simulation_plan",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["simulation_orchestrator"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["simulation_orchestrator"].tool_names,
)


class SimulationOrchestratorAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["SimulationOrchestratorAgentService", "CONFIG"]

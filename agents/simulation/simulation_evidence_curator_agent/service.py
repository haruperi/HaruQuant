"""Service for Simulation Evidence Curator Agent."""

from __future__ import annotations

from agents.simulation.shared.capabilities import AGENT_CAPABILITIES
from agents.simulation.shared.constants import POLICY_VERSION, PROMPT_VERSION
from agents.simulation.shared.simulation_agent import GenericSimulationAgentService, SimulationAgentConfig

CONFIG = SimulationAgentConfig(
    agent_name="simulation_evidence_curator_agent",
    display_name="Simulation Evidence Curator Agent",
    artifact_type="simulation_evidence_index",
    prompt_version=PROMPT_VERSION,
    policy_version=POLICY_VERSION,
    allowed_actions=AGENT_CAPABILITIES["simulation_evidence_curator_agent"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["simulation_evidence_curator_agent"].tool_names,
)


class SimulationEvidenceCuratorAgentService(GenericSimulationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["SimulationEvidenceCuratorAgentService", "CONFIG"]

"""Service for Risk Orchestrator."""

from __future__ import annotations

from agents.risk.shared.contracts import AGENT_CAPABILITIES
from agents.risk.shared.risk_agent import GenericRiskAgent, RiskAgentConfig

CONFIG = RiskAgentConfig(
    agent_name="risk_orchestrator",
    display_name="Risk Orchestrator",
    artifact_type="risk_department_response",
    allowed_actions=AGENT_CAPABILITIES["risk_orchestrator"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["risk_orchestrator"].tool_names,
)


class RiskOrchestratorAgent(GenericRiskAgent):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["RiskOrchestratorAgent", "CONFIG"]

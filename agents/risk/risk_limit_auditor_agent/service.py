"""Service for Risk Limit Auditor."""

from __future__ import annotations

from agents.risk.shared.contracts import AGENT_CAPABILITIES
from agents.risk.shared.risk_agent import GenericRiskAgent, RiskAgentConfig

CONFIG = RiskAgentConfig(
    agent_name="risk_limit_auditor",
    display_name="Risk Limit Auditor",
    artifact_type="risk_limit_audit",
    allowed_actions=AGENT_CAPABILITIES["risk_limit_auditor"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["risk_limit_auditor"].tool_names,
)


class RiskLimitAuditorAgent(GenericRiskAgent):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["RiskLimitAuditorAgent", "CONFIG"]

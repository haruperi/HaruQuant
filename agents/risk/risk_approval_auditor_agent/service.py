"""Service for Risk Approval Auditor."""

from __future__ import annotations

from agents.risk.shared.contracts import AGENT_CAPABILITIES
from agents.risk.shared.risk_agent import GenericRiskAgent, RiskAgentConfig

CONFIG = RiskAgentConfig(
    agent_name="risk_approval_auditor",
    display_name="Risk Approval Auditor",
    artifact_type="risk_approval_audit",
    allowed_actions=AGENT_CAPABILITIES["risk_approval_auditor"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["risk_approval_auditor"].tool_names,
)


class RiskApprovalAuditorAgent(GenericRiskAgent):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["RiskApprovalAuditorAgent", "CONFIG"]

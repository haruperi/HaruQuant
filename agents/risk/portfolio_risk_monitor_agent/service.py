"""Service for Portfolio Risk Monitor."""

from __future__ import annotations

from agents.risk.shared.contracts import AGENT_CAPABILITIES
from agents.risk.shared.risk_agent import GenericRiskAgent, RiskAgentConfig

CONFIG = RiskAgentConfig(
    agent_name="portfolio_risk_monitor",
    display_name="Portfolio Risk Monitor",
    artifact_type="portfolio_risk_report",
    allowed_actions=AGENT_CAPABILITIES["portfolio_risk_monitor"].allowed_actions,
    tool_names=AGENT_CAPABILITIES["portfolio_risk_monitor"].tool_names,
)


class PortfolioRiskMonitorAgent(GenericRiskAgent):
    def __init__(self) -> None:
        super().__init__(CONFIG)


__all__ = ["PortfolioRiskMonitorAgent", "CONFIG"]

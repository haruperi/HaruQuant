"""Risk Reviewer Department facade."""

from backend.agents.risk_governor_agent import RiskGovernorAgentAdapter
from backend.services.risk import *  # noqa: F403

__all__ = ["RiskGovernorAgentAdapter"]

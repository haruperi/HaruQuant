"""Portfolio Manager facade over current portfolio advisory services."""

from backend.agents.portfolio_agent import PORTFOLIO_AGENT_INSTRUCTION, PortfolioAgentWrapper
from services.risk.portfolio import *  # noqa: F403

PORTFOLIO_MANAGER_DEPARTMENT = "portfolio_manager"

__all__ = [
    "PORTFOLIO_MANAGER_DEPARTMENT",
    "PORTFOLIO_AGENT_INSTRUCTION",
    "PortfolioAgentWrapper",
]

"""Portfolio Manager facade over current portfolio advisory services."""

from backend_retiring.agents.portfolio_agent import PORTFOLIO_AGENT_INSTRUCTION, PortfolioAgentWrapper
from haruquant.risk import *

PORTFOLIO_MANAGER_DEPARTMENT = "portfolio_manager"

__all__ = [
    "PORTFOLIO_MANAGER_DEPARTMENT",
    "PORTFOLIO_AGENT_INSTRUCTION",
    "PortfolioAgentWrapper",
]

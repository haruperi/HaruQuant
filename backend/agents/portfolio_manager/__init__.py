"""Portfolio Manager Department facade."""

from backend.agents.portfolio_agent import PORTFOLIO_AGENT_INSTRUCTION, PortfolioAgentWrapper
from services.risk.portfolio import *  # noqa: F403

__all__ = ["PORTFOLIO_AGENT_INSTRUCTION", "PortfolioAgentWrapper"]

"""Strategy Reviewer facade over current strategy and code review agents."""

from backend_retiring.agents.chat.strategy_code_review_agent import StrategyCodeReviewAgent
from backend_retiring.agents.strategy_agent import STRATEGY_AGENT_INSTRUCTION, StrategyAgentWrapper

STRATEGY_REVIEWER_DEPARTMENT = "strategy_reviewer"

__all__ = [
    "STRATEGY_REVIEWER_DEPARTMENT",
    "STRATEGY_AGENT_INSTRUCTION",
    "StrategyAgentWrapper",
    "StrategyCodeReviewAgent",
]

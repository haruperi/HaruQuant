"""Strategy Creator facade over the existing strategy creator agent."""

from backend_retiring.agents.strategy_creator_agent import (
    STRATEGY_CREATOR_AGENT_INSTRUCTION,
    StrategyCreatorAgent,
    StrategyCreatorResult,
)

STRATEGY_CREATOR_DEPARTMENT = "strategy_creator"

__all__ = [
    "STRATEGY_CREATOR_DEPARTMENT",
    "STRATEGY_CREATOR_AGENT_INSTRUCTION",
    "StrategyCreatorAgent",
    "StrategyCreatorResult",
]

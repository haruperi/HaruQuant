"""Research Department agent facade."""

from backend.agents.regime_agent import REGIME_AGENT_INSTRUCTION, RegimeAgentWrapper
from backend.agents.research_agent import RESEARCH_AGENT_INSTRUCTION, ResearchAgentWrapper
from backend.agents.volatility_agent import VOLATILITY_AGENT_INSTRUCTION, VolatilityAgentWrapper

__all__ = [
    "REGIME_AGENT_INSTRUCTION",
    "RESEARCH_AGENT_INSTRUCTION",
    "VOLATILITY_AGENT_INSTRUCTION",
    "RegimeAgentWrapper",
    "ResearchAgentWrapper",
    "VolatilityAgentWrapper",
]

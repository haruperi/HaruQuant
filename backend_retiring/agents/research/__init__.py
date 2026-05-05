"""Research Department agent facade."""

from backend_retiring.agents.regime_agent import REGIME_AGENT_INSTRUCTION, RegimeAgentWrapper
from backend_retiring.agents.research_agent import RESEARCH_AGENT_INSTRUCTION, ResearchAgentWrapper
from backend_retiring.agents.volatility_agent import VOLATILITY_AGENT_INSTRUCTION, VolatilityAgentWrapper

__all__ = [
    "REGIME_AGENT_INSTRUCTION",
    "RESEARCH_AGENT_INSTRUCTION",
    "VOLATILITY_AGENT_INSTRUCTION",
    "RegimeAgentWrapper",
    "ResearchAgentWrapper",
    "VolatilityAgentWrapper",
]
"""Research Department agents."""

from backend_retiring.agents.research.agent import (
    MarketIntelligenceAgent,
    RegimeAgentWrapper,
    ResearchAgentWrapper,
    StrategyScoutAgent,
    TechnicalAnalystAgent,
    VolatilityAgentWrapper,
)

__all__ = [
    "MarketIntelligenceAgent",
    "RegimeAgentWrapper",
    "ResearchAgentWrapper",
    "StrategyScoutAgent",
    "TechnicalAnalystAgent",
    "VolatilityAgentWrapper",
]

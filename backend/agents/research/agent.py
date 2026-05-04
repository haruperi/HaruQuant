"""Research Department facade over current market research agents."""

from backend.agents.research.market_intelligence_agent import MarketIntelligenceAgent
from backend.agents.research.strategy_scout_agent import StrategyScoutAgent
from backend.agents.research.technical_analyst_agent import TechnicalAnalystAgent
from backend.agents.regime_agent import REGIME_AGENT_INSTRUCTION, RegimeAgentWrapper
from backend.agents.research_agent import RESEARCH_AGENT_INSTRUCTION, ResearchAgentWrapper
from backend.agents.volatility_agent import VOLATILITY_AGENT_INSTRUCTION, VolatilityAgentWrapper

RESEARCH_DEPARTMENT = "research"

__all__ = [
    "RESEARCH_DEPARTMENT",
    "REGIME_AGENT_INSTRUCTION",
    "RESEARCH_AGENT_INSTRUCTION",
    "VOLATILITY_AGENT_INSTRUCTION",
    "MarketIntelligenceAgent",
    "RegimeAgentWrapper",
    "ResearchAgentWrapper",
    "StrategyScoutAgent",
    "TechnicalAnalystAgent",
    "VolatilityAgentWrapper",
]

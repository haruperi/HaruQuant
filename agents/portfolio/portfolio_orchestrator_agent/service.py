from agents.portfolio.shared.portfolio_agent import GenericPortfolioAgent
from .deterministic_policy import CONFIG
class PortfolioOrchestratorAgent(GenericPortfolioAgent):
    def __init__(self) -> None:
        super().__init__(CONFIG)
__all__ = ["PortfolioOrchestratorAgent", "CONFIG"]

"""Contracts for the Strategy Risk Assumption Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyRiskAssumptionAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Risk Assumption Agent."""

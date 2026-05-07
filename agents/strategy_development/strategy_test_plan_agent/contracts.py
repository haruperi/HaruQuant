"""Contracts for the Strategy Test Plan Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyTestPlanAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Test Plan Agent."""

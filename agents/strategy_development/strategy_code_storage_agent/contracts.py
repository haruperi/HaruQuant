"""Contracts for the Strategy Code Storage Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyCodeStorageAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Code Storage Agent."""

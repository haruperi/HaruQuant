"""Contracts for the Strategy Creator Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyCreatorAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Creator Agent."""

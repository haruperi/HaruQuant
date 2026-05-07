"""Contracts for the Strategy Handoff Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyHandoffAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Handoff Agent."""

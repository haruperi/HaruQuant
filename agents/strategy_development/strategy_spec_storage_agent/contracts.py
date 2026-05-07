"""Contracts for the Strategy Spec Storage Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategySpecStorageAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Spec Storage Agent."""

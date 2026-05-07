"""Contracts for the Strategy Reviewer Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyReviewerAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Reviewer Agent."""

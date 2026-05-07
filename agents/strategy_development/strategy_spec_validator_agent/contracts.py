"""Contracts for the Strategy Spec Validator Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategySpecValidatorAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Spec Validator Agent."""

"""Contracts for the Strategy Cost & Execution Assumption Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyCostExecutionAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Cost & Execution Assumption Agent."""

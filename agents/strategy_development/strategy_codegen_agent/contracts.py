"""Contracts for the Strategy Codegen Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyCodegenAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Codegen Agent."""

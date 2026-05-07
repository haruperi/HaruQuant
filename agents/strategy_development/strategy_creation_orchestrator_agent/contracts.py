"""Contracts for the Strategy Creation Orchestrator Agent."""

from __future__ import annotations

from agents.strategy_development.shared.contracts import StrategyCreationPayload


class StrategyCreationOrchestratorAgentPayload(StrategyCreationPayload):
    """Validated payload for Strategy Creation Orchestrator Agent."""

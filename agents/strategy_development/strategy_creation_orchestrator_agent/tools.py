"""Declared tools for the Strategy Creation Orchestrator Agent."""

from __future__ import annotations

from agents.strategy_development.shared.permissions import assert_strategy_tool_allowed

ALLOWED_TOOL_NAMES = ('read_research_handoff', 'run_strategy_creation_agents', 'save_strategy_creation_package')


def get_strategy_creation_snapshot() -> dict:
    assert_strategy_tool_allowed("get_strategy_creation_snapshot")
    return {"department": "Strategy Creation Department", "status": "ready"}


TOOLS = [get_strategy_creation_snapshot]

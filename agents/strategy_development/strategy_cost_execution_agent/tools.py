"""Declared tools for the Strategy Cost & Execution Assumption Agent."""

from __future__ import annotations

from agents.strategy_development.shared.permissions import assert_strategy_tool_allowed

ALLOWED_TOOL_NAMES = ('read_strategy_spec', 'read_execution_policy')


def get_strategy_creation_snapshot() -> dict:
    assert_strategy_tool_allowed("get_strategy_creation_snapshot")
    return {"department": "Strategy Creation Department", "status": "ready"}


TOOLS = [get_strategy_creation_snapshot]

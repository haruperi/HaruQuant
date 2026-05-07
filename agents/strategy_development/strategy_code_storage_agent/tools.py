"""Declared tools for the Strategy Code Storage Agent."""

from __future__ import annotations

from agents.strategy_development.shared.permissions import assert_strategy_tool_allowed

ALLOWED_TOOL_NAMES = ('read_strategy_code_package', 'write_strategy_code_memory')


def get_strategy_creation_snapshot() -> dict:
    assert_strategy_tool_allowed("get_strategy_creation_snapshot")
    return {"department": "Strategy Creation Department", "status": "ready"}


TOOLS = [get_strategy_creation_snapshot]

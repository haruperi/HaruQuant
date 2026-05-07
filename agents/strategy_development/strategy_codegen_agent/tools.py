"""Declared tools for the Strategy Codegen Agent."""

from __future__ import annotations

from agents.strategy_development.shared.permissions import assert_strategy_tool_allowed

ALLOWED_TOOL_NAMES = ('read_approved_strategy_spec', 'write_generated_code_artifacts')


def get_strategy_creation_snapshot() -> dict:
    assert_strategy_tool_allowed("get_strategy_creation_snapshot")
    return {"department": "Strategy Creation Department", "status": "ready"}


TOOLS = [get_strategy_creation_snapshot]

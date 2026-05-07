"""Declared tools for the Macro and Fundamental Context Agent."""

from __future__ import annotations

from typing import Any

from agents.research.shared.permissions import assert_research_tool_allowed

ALLOWED_TOOL_NAMES = ('get_macro_calendar', 'get_fundamental_snapshot', 'get_rate_policy_context', 'save_macro_fundamental_report')


def get_research_tool_snapshot(symbol: str | None = None) -> dict[str, Any]:
    """Return a deterministic read-only placeholder snapshot for local tests."""
    assert_research_tool_allowed("get_research_tool_snapshot")
    return {"symbol": symbol, "data_quality_score": 0.8, "sample_size": 250, "volatility_state": "normal"}


TOOLS = [get_research_tool_snapshot]

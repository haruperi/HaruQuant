"""Declared tools for the Cross-Asset / Intermarket Agent."""

from __future__ import annotations

from typing import Any

from agents.research.shared.permissions import assert_research_tool_allowed

ALLOWED_TOOL_NAMES = ('get_cross_asset_data', 'calculate_correlations', 'detect_intermarket_divergence', 'save_cross_asset_report')


def get_research_tool_snapshot(symbol: str | None = None) -> dict[str, Any]:
    """Return a deterministic read-only placeholder snapshot for local tests."""
    assert_research_tool_allowed("get_research_tool_snapshot")
    return {"symbol": symbol, "data_quality_score": 0.8, "sample_size": 250, "volatility_state": "normal"}


TOOLS = [get_research_tool_snapshot]

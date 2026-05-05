from __future__ import annotations

from haruquant.execution import evaluate_tool_health


def test_evaluate_tool_health_detects_degraded_downstreams() -> None:
    result = evaluate_tool_health(
        {
            "mt5_mcp": "healthy",
            "market_data_mcp": "degraded",
            "sql_mcp": "unhealthy",
        }
    )
    assert result.degraded is True
    assert result.failing_tools == ("market_data_mcp", "sql_mcp")


def test_evaluate_tool_health_accepts_healthy_and_disabled_tools() -> None:
    result = evaluate_tool_health(
        {
            "mt5_mcp": "healthy",
            "redis": "disabled",
        }
    )
    assert result.degraded is False
    assert result.status == "healthy"

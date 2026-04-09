from __future__ import annotations

import pytest

from backend.agents import ToolAllowlistMiddleware, ToolPolicyError


def test_tool_allowlist_middleware_allows_declared_tools() -> None:
    middleware = ToolAllowlistMiddleware()

    decision = middleware.enforce(
        allowed_tools=("market.snapshot", "risk.evaluate"),
        requested_tools=("market.snapshot",),
    )

    assert decision.allowed is True
    assert decision.allowed_tools == ("market.snapshot",)
    assert decision.blocked_tools == ()


def test_tool_allowlist_middleware_blocks_unknown_tools() -> None:
    middleware = ToolAllowlistMiddleware()

    with pytest.raises(ToolPolicyError, match="disallowed tools requested: mt5.place_order"):
        middleware.enforce(
            allowed_tools=("market.snapshot", "risk.evaluate"),
            requested_tools=("market.snapshot", "mt5.place_order"),
        )

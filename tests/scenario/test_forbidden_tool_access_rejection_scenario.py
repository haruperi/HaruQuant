from __future__ import annotations

import pytest

from backend.agents.runtime.tool_policy import ToolAllowlistMiddleware, ToolPolicyError


def test_agent_attempt_to_call_forbidden_external_tool_is_rejected() -> None:
    middleware = ToolAllowlistMiddleware()

    with pytest.raises(ToolPolicyError, match="disallowed tools requested: external.http.post"):
        middleware.enforce(
            allowed_tools=("risk.read_snapshot", "research.fetch_sources"),
            requested_tools=("research.fetch_sources", "external.http.post"),
        )


from __future__ import annotations

import pytest

from agents.permissions import (
    AgentToolPermissionError,
    AgentToolPermissionService,
)
from agents.runtime.tool_policy import ToolAllowlistMiddleware, ToolPolicyError


def test_agent_permission_allows_registered_read_only_tool() -> None:
    service = AgentToolPermissionService()

    decision = service.enforce(agent_name="research", tool_name="get_symbol_data")

    assert decision.allowed is True
    assert decision.tool_definition is not None
    assert decision.tool_definition.risk_level == "read_only"


def test_agent_permission_blocks_tool_not_allowed_for_agent() -> None:
    service = AgentToolPermissionService()

    decision = service.evaluate(
        agent_name="research",
        tool_name="place_live_order",
        has_human_approval=True,
        has_risk_governor_approval=True,
    )

    assert decision.allowed is False
    assert decision.reason == "tool_not_allowed_for_agent"


def test_agent_permission_blocks_critical_tool_without_required_approvals() -> None:
    service = AgentToolPermissionService()

    missing_both = service.evaluate(agent_name="execution", tool_name="place_live_order")
    missing_risk = service.evaluate(
        agent_name="execution",
        tool_name="place_live_order",
        has_human_approval=True,
    )
    allowed = service.evaluate(
        agent_name="execution",
        tool_name="place_live_order",
        has_human_approval=True,
        has_risk_governor_approval=True,
    )

    assert missing_both.allowed is False
    assert missing_both.reason == "missing_human_approval"
    assert missing_risk.allowed is False
    assert missing_risk.reason == "missing_risk_governor_approval"
    assert allowed.allowed is True


def test_agent_permission_enforce_raises_for_unknown_tool() -> None:
    service = AgentToolPermissionService()

    with pytest.raises(AgentToolPermissionError, match="unknown_tool"):
        service.enforce(agent_name="ceo", tool_name="invented_tool")


def test_runtime_tool_middleware_can_enforce_phase5_permissions() -> None:
    middleware = ToolAllowlistMiddleware()

    decision = middleware.enforce_agent_tool(
        agent_name="strategy_creator",
        tool_name="create_strategy_spec",
    )
    assert decision.allowed is True

    with pytest.raises(ToolPolicyError, match="missing_human_approval"):
        middleware.enforce_agent_tool(
            agent_name="execution",
            tool_name="place_live_order",
        )

"""Permission profile for Research Department agents."""

from __future__ import annotations

from typing import Any

RESEARCH_PERMISSION_PROFILE_NAME = "research_read_only_v1"
RESEARCH_PERMISSION_PROFILE: dict[str, bool] = {
    "can_read_market_data": True,
    "can_read_historical_data": True,
    "can_read_evidence_memory": True,
    "can_lookup_approved_external_research": True,
    "can_write_evidence_memory": True,
    "can_execute_trade": False,
    "can_place_order": False,
    "can_approve_risk": False,
    "can_modify_portfolio": False,
    "can_access_broker_execution": False,
}


def assert_research_tool_allowed(tool_name: str, metadata: dict[str, Any] | None = None) -> None:
    metadata = metadata or {}
    if metadata.get("execution_tool") or tool_name in {"place_trade", "execute_order"}:
        raise PermissionError(f"Research tool is not allowed to execute trades: {tool_name}")
    if metadata.get("risk_approval_tool") or tool_name == "approve_risk":
        raise PermissionError(f"Research tool is not allowed to approve risk: {tool_name}")

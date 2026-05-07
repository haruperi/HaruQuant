"""Permission profiles for Strategy Creation Department agents."""

from __future__ import annotations

STRATEGY_CREATION_PERMISSION_PROFILES = {
    "strategy_creation_read_only_v1": {"can_read_research": True, "can_execute_trade": False, "can_approve_risk": False},
    "strategy_spec_write_v1": {"can_write_specs": True, "can_execute_trade": False, "can_approve_risk": False},
    "strategy_codegen_write_v1": {"can_write_code_artifacts": True, "can_execute_trade": False, "can_approve_risk": False},
    "strategy_review_read_only_v1": {"can_review_code": True, "can_execute_trade": False, "can_approve_risk": False},
    "strategy_handoff_write_v1": {"can_write_handoff": True, "can_execute_trade": False, "can_approve_risk": False},
}


def assert_strategy_tool_allowed(tool_name: str) -> None:
    if tool_name in {"execute_trade", "execute_order", "approve_risk", "send_order"}:
        raise PermissionError(f"Strategy Creation tool is forbidden: {tool_name}")

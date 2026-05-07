"""Declared tools for the Strategy Reviewer Agent."""

from __future__ import annotations

from agents.strategy_development.shared.permissions import assert_strategy_tool_allowed

ALLOWED_TOOL_NAMES = ('read_strategy_spec', 'read_generated_code_package', 'run_static_strategy_review')


def get_strategy_creation_snapshot() -> dict:
    assert_strategy_tool_allowed("get_strategy_creation_snapshot")
    return {"department": "Strategy Creation Department", "status": "ready"}


class StrategySpecValidator:
    """Compatibility validator used by control-plane phase tests."""

    def validate(self, spec: dict) -> dict:
        missing = [field for field in ("strategy_id", "entry_rules", "exit_rules") if field not in spec]
        return {"valid": not missing, "missing": missing}


TOOLS = [get_strategy_creation_snapshot]

__all__ = ["ALLOWED_TOOL_NAMES", "StrategySpecValidator", "TOOLS", "get_strategy_creation_snapshot"]

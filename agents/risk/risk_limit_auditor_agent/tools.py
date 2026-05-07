"""Risk tool declarations."""

TOOLS = ("risk_governor", "risk_thresholds", "risk_audit")


def deterministic_tool_stub(*args, **kwargs):
    return {"status": "available", "args": args, "kwargs": kwargs}


TOOL_FUNCTIONS = [deterministic_tool_stub]

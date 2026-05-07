"""Runtime factory for Live Execution Agent."""

from .prompts import SYSTEM_INSTRUCTIONS


def build_agent() -> dict[str, str]:
    return {"name": "live_execution_agent", "instructions": SYSTEM_INSTRUCTIONS, "runtime": "deterministic_stub"}

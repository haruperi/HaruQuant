"""Runtime factory for the internal Planner Agent."""

from .prompts import SYSTEM_INSTRUCTIONS


def build_agent() -> dict[str, str]:
    return {"name": "internal_planner_agent", "instructions": SYSTEM_INSTRUCTIONS, "runtime": "deterministic_wrapper"}

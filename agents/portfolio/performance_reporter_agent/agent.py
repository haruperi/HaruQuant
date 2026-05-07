from .prompts import SYSTEM_INSTRUCTIONS

def build_agent() -> dict[str, str]:
    return {"name": "performance_reporter_agent", "instructions": SYSTEM_INSTRUCTIONS, "runtime": "deterministic_stub"}

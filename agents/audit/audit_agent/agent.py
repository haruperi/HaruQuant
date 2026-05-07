from .prompts import SYSTEM_INSTRUCTIONS

def build_agent() -> dict[str, str]:
    return {"name": "audit_agent", "instructions": SYSTEM_INSTRUCTIONS, "runtime": "deterministic_stub"}

"""Canonical identifier helpers for migration-era services."""

from __future__ import annotations

from secrets import token_hex


ID_PREFIXES = {
    "workflow": "wf",
    "correlation": "corr",
    "causation": "evt",
    "hypothesis": "hyp",
    "proposal": "prop",
    "risk_decision": "risk",
    "execution_intent": "exec",
    "receipt": "rcpt",
    "session": "sess",
    "incident": "inc",
    "replay_bundle": "rpb",
    "approval": "appr",
    "strategy": "strat",
    "promotion": "prom",
}


def generate_prefixed_id(prefix: str, *, size_bytes: int = 8) -> str:
    """Generate a lowercase prefixed identifier."""

    normalized = prefix.strip().lower()
    if not normalized:
        raise ValueError("prefix must be non-empty")
    if size_bytes <= 0:
        raise ValueError("size_bytes must be positive")
    return f"{normalized}_{token_hex(size_bytes)}"


def generate_id(kind: str, *, size_bytes: int = 8) -> str:
    """Generate an identifier using the canonical prefix for a known kind."""

    try:
        prefix = ID_PREFIXES[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown id kind: {kind}") from exc
    return generate_prefixed_id(prefix, size_bytes=size_bytes)

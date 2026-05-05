"""Firm-facing audit tool registry facade."""

from services.strategy.evidence.audit import *  # noqa: F403

TOOL_DOMAIN = "audit"
CANONICAL_SOURCES = (
    "services.strategy.evidence.audit",
    "services.strategy.evidence",
    "backend.contracts.replay_bundle",
)

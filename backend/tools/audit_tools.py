"""Firm-facing audit tool registry facade."""

from backend.services.audit import *  # noqa: F403

TOOL_DOMAIN = "audit"
CANONICAL_SOURCES = (
    "backend.services.audit",
    "backend.services.evidence",
    "backend.contracts.replay_bundle",
)

"""Firm-facing audit tool registry facade."""

from haruquant.strategy import *

TOOL_DOMAIN = "audit"
CANONICAL_SOURCES = (
    "services.strategy.evidence.audit",
    "services.strategy.evidence",
    "backend.contracts.replay_bundle",
)

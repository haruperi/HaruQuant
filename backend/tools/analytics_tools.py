"""Firm-facing analytics tool registry facade."""

from backend.services.analytics import *  # noqa: F403

TOOL_DOMAIN = "analytics"
CANONICAL_SOURCES = (
    "backend.services.analytics",
    "backend.services.performance",
    "backend.services.research.core_metrics",
)

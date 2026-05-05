"""Firm-facing analytics tool registry facade."""

from services.analytics import *  # noqa: F403

TOOL_DOMAIN = "analytics"
CANONICAL_SOURCES = (
    "services.analytics",
    "services.execution.performance",
    "services.research.core_metrics",
)

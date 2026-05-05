"""Firm-facing analytics tool registry facade."""

from haruquant.analytics import *

TOOL_DOMAIN = "analytics"
CANONICAL_SOURCES = (
    "services.analytics",
    "services.execution.performance",
    "services.research.core_metrics",
)

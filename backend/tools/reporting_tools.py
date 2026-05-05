"""Firm-facing reporting tool registry facade."""

from services.analytics.overview import *  # noqa: F403
from services.strategy.evidence import *  # noqa: F403
from services.execution.performance import *  # noqa: F403

TOOL_DOMAIN = "reporting"
REPORT_OUTPUT_ROOT = "reports"

"""Firm-facing reporting tool registry facade."""

from backend.services.analytics.overview import *  # noqa: F403
from backend.services.evidence import *  # noqa: F403
from backend.services.performance import *  # noqa: F403

TOOL_DOMAIN = "reporting"
REPORT_OUTPUT_ROOT = "reports"

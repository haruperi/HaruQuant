"""Risk and Board approval facade."""

from backend.services.approval import *  # noqa: F403
from backend.services.risk.decisions import *  # noqa: F403

APPROVALS_FACADE = "backend.risk.approvals"

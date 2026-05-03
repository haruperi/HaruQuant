"""Paper execution facade over simulation and shadow execution services."""

from backend.services.shadow import *  # noqa: F403
from backend.services.simulation import *  # noqa: F403

PAPER_BROKER_FACADE = "backend.execution.paper_broker"

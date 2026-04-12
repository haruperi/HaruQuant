"""Shared logging helpers for migration-era services."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any, Iterator

from backend.common.logger import StructlogAdapter, logger as app_logger


@dataclass(frozen=True)
class WorkflowLogContext:
    """Normalized log context for workflow-aware services."""

    workflow_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    run_id: str = ""
    trace_id: str = ""
    service: str = ""
    environment: str = ""

    def to_log_extra(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value}


def get_service_logger(name: str) -> StructlogAdapter:
    """Return a service-specific logger bound to the global app logger core."""

    return app_logger.bind(component=name)


@contextmanager
def bind_log_context(
    logger: StructlogAdapter,
    context: WorkflowLogContext,
    **extra: Any,
) -> Iterator[StructlogAdapter]:
    """Bind standard workflow/correlation context to a logger."""

    payload = context.to_log_extra()
    payload.update(extra)
    with logger.contextualize(**payload) as bound:
        yield bound

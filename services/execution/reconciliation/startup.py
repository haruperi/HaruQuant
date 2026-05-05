"""Startup-time reconciliation loading helpers."""

from __future__ import annotations

from collections.abc import Iterable

from data.database import ExecutionIntentRecord, ExecutionRepository
from backend_retiring.orchestration.workflow import ProposalState

DEFAULT_IN_FLIGHT_EXECUTION_STATUSES: tuple[str, ...] = (
    ProposalState.EXECUTION_PENDING.value,
    ProposalState.SENT.value,
    ProposalState.ACKNOWLEDGED.value,
    ProposalState.PARTIALLY_FILLED.value,
)


class ReconciliationStartupLoader:
    """Loads execution intents that must be reconciled before live recovery."""

    def __init__(
        self,
        execution_repository: ExecutionRepository,
        *,
        in_flight_statuses: Iterable[str] = DEFAULT_IN_FLIGHT_EXECUTION_STATUSES,
    ) -> None:
        self._execution_repository = execution_repository
        self._in_flight_statuses = tuple(in_flight_statuses)

    def load_in_flight_execution_intents(self) -> list[ExecutionIntentRecord]:
        return self._execution_repository.list_intents_by_statuses(self._in_flight_statuses)

"""Execution send-attempt persistence helpers."""

from __future__ import annotations

import hashlib

from backend.contracts.serialization import canonical_json_dumps
from backend.db import ExecutionRepository, ExecutionSendAttemptRecord


class ExecutionAttemptPersistenceService:
    """Persist send attempts with stable submitted-payload hashing."""

    def __init__(self, repository: ExecutionRepository) -> None:
        self._repository = repository

    def persist_attempt(
        self,
        *,
        execution_intent_id: str,
        submitted_payload: dict[str, object],
        transport_status: str,
        broker_request_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        finished_at: str | None = None,
        latency_ms: int | None = None,
    ) -> ExecutionSendAttemptRecord:
        attempts = self._repository.list_send_attempts_for_intent(execution_intent_id)
        payload_hash = hashlib.sha256(
            canonical_json_dumps(submitted_payload).encode("utf-8")
        ).hexdigest()
        return self._repository.add_send_attempt(
            execution_intent_id=execution_intent_id,
            attempt_no=len(attempts) + 1,
            submitted_payload_hash=payload_hash,
            transport_status=transport_status,
            broker_request_ref=broker_request_ref,
            error_code=error_code,
            error_message=error_message,
            finished_at=finished_at,
            latency_ms=latency_ms,
        )

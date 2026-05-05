"""Workflow-timeout detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from services.utils.logger import logger
from services.utils import Clock, SystemClock
from data.database import WorkflowRecord, WorkflowRepository


TERMINAL_WORKFLOW_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}


@dataclass(frozen=True)
class WorkflowTimeoutResult:
    """Result of workflow timeout detection and transition."""

    timed_out: bool
    transitioned: bool
    reason_code: str


class WorkflowTimeoutService:
    """Detect and apply workflow timeout transitions."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self._repository = repository

    def evaluate(
        self,
        workflow: WorkflowRecord,
        *,
        clock: Clock | None = None,
    ) -> WorkflowTimeoutResult:
        timeout_seconds = _extract_timeout_seconds(workflow.timeout_policy_json)
        if timeout_seconds is None or workflow.state in TERMINAL_WORKFLOW_STATES:
            return WorkflowTimeoutResult(
                timed_out=False,
                transitioned=False,
                reason_code="timeout_not_applicable",
            )

        active_clock = clock or SystemClock()
        reference_time = datetime.fromisoformat(workflow.updated_at.replace("Z", "+00:00"))
        elapsed = (active_clock.now() - reference_time).total_seconds()
        if elapsed <= timeout_seconds:
            return WorkflowTimeoutResult(
                timed_out=False,
                transitioned=False,
                reason_code="within_timeout_window",
            )

        self._repository.update_workflow_state(
            workflow_id=workflow.workflow_id,
            expected_version=workflow.version_no,
            state="TIMED_OUT",
            terminal_reason="workflow_timeout_detected",
            completed_at=active_clock.now().isoformat().replace("+00:00", "Z"),
        )
        return WorkflowTimeoutResult(
            timed_out=True,
            transitioned=True,
            reason_code="workflow_timeout_detected",
        )


def _extract_timeout_seconds(timeout_policy_json: str) -> int | None:
    payload = json.loads(timeout_policy_json or "{}")
    timeout_seconds = payload.get("timeout_seconds")
    if timeout_seconds is None:
        return None
    return int(timeout_seconds)

"""Workflow persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from haruquant.utils import logger
from backend.data.database import WorkflowRepository

from .states import WorkflowState


@dataclass(frozen=True)
class WorkflowTransitionEvent:
    """Append-only workflow transition payload."""

    workflow_id: str
    from_state: WorkflowState
    to_state: WorkflowState
    actor_type: str
    actor_id: str
    correlation_id: str
    phase_name: str | None = None
    transition_reason: str | None = None
    causation_id: str | None = None
    metadata_json: str = "{}"


class WorkflowTransitionLogger:
    """Append workflow transition history using the workflow repository."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def append(self, event: WorkflowTransitionEvent) -> int:
        return self.repository.append_transition(
            workflow_id=event.workflow_id,
            from_state=event.from_state.value,
            to_state=event.to_state.value,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            correlation_id=event.correlation_id,
            phase_name=event.phase_name,
            transition_reason=event.transition_reason,
            causation_id=event.causation_id,
            metadata_json=event.metadata_json,
        )


@dataclass(frozen=True)
class WorkflowStepRecord:
    """Stored workflow step row."""

    step_id: str
    workflow_id: str
    step_order: int
    step_type: str
    assigned_agent: str | None
    input_contract_type: str | None
    input_ref: str | None
    output_contract_type: str | None
    output_ref: str | None
    status: str
    started_at: str | None
    completed_at: str | None
    latency_ms: int | None
    iteration_no: int
    metadata_json: str


@dataclass(frozen=True)
class WorkflowStepRequest:
    """Payload used to append one ordered workflow step."""

    step_id: str
    workflow_id: str
    step_type: str
    status: str
    assigned_agent: str | None = None
    input_contract_type: str | None = None
    input_ref: str | None = None
    output_contract_type: str | None = None
    output_ref: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    latency_ms: int | None = None
    iteration_no: int = 0
    metadata_json: str = "{}"


class WorkflowStepRecorder:
    """Append ordered workflow steps into the workflow_steps table."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def record(self, request: WorkflowStepRequest) -> WorkflowStepRecord:
        with self._connect() as connection:
            current_order = connection.execute(
                """
                SELECT COALESCE(MAX(step_order), 0)
                FROM core_workflow_steps
                WHERE workflow_id = ?
                """,
                (request.workflow_id,),
            ).fetchone()[0]
            next_order = int(current_order) + 1

            connection.execute(
                """
                INSERT INTO core_workflow_steps (
                    step_id,
                    workflow_id,
                    step_order,
                    step_type,
                    assigned_agent,
                    input_contract_type,
                    input_ref,
                    output_contract_type,
                    output_ref,
                    status,
                    started_at,
                    completed_at,
                    latency_ms,
                    iteration_no,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.step_id,
                    request.workflow_id,
                    next_order,
                    request.step_type,
                    request.assigned_agent,
                    request.input_contract_type,
                    request.input_ref,
                    request.output_contract_type,
                    request.output_ref,
                    request.status,
                    request.started_at,
                    request.completed_at,
                    request.latency_ms,
                    request.iteration_no,
                    request.metadata_json,
                ),
            )

            row = connection.execute(
                "SELECT * FROM core_workflow_steps WHERE step_id = ?",
                (request.step_id,),
            ).fetchone()

        if row is None:
            raise LookupError(f"workflow step not found after insert: {request.step_id}")
        return WorkflowStepRecord(**dict(row))

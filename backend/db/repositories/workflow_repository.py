"""Workflow repository over the SQLite baseline schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any

from apps.core import StaleVersionError, apply_version_update


@dataclass(frozen=True)
class WorkflowRecord:
    """Stored workflow state."""

    workflow_id: str
    workflow_type: str
    environment: str
    operating_mode: str
    state: str
    objective: str
    scope_json: str
    initiator_type: str
    initiator_id: str
    timeout_policy_json: str
    stop_conditions_json: str
    current_step_id: str | None
    version_no: int
    created_at: str
    updated_at: str
    completed_at: str | None
    terminal_reason: str | None


@dataclass(frozen=True)
class IncidentRecord:
    """Stored incident state."""

    incident_id: str
    severity: str
    state: str
    alert_type: str
    source: str
    summary: str
    opened_at: str
    resolved_at: str | None
    recommended_action: str | None
    metadata_json: str


class WorkflowRepository:
    """Minimal persistence wrapper for workflow state and transitions."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_workflow(
        self,
        *,
        workflow_id: str,
        workflow_type: str,
        environment: str,
        operating_mode: str,
        state: str,
        objective: str,
        scope_json: str = "{}",
        initiator_type: str,
        initiator_id: str,
        timeout_policy_json: str = "{}",
        stop_conditions_json: str = "[]",
        current_step_id: str | None = None,
        completed_at: str | None = None,
        terminal_reason: str | None = None,
    ) -> WorkflowRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO core_workflows (
                    workflow_id,
                    workflow_type,
                    environment,
                    operating_mode,
                    state,
                    objective,
                    scope_json,
                    initiator_type,
                    initiator_id,
                    timeout_policy_json,
                    stop_conditions_json,
                    current_step_id,
                    completed_at,
                    terminal_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    workflow_type,
                    environment,
                    operating_mode,
                    state,
                    objective,
                    scope_json,
                    initiator_type,
                    initiator_id,
                    timeout_policy_json,
                    stop_conditions_json,
                    current_step_id,
                    completed_at,
                    terminal_reason,
                ),
            )

        record = self.get_workflow(workflow_id)
        if record is None:
            raise LookupError(f"workflow not found after create: {workflow_id}")
        return record

    def get_workflow(self, workflow_id: str) -> WorkflowRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def update_workflow_state(
        self,
        *,
        workflow_id: str,
        expected_version: int,
        state: str,
        current_step_id: str | None = None,
        completed_at: str | None = None,
        terminal_reason: str | None = None,
    ) -> WorkflowRecord:
        current = self.get_workflow(workflow_id)
        if current is None:
            raise LookupError(f"workflow not found: {workflow_id}")

        next_state = apply_version_update(
            expected_version=expected_version,
            current_version=current.version_no,
        )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE core_workflows
                SET state = ?,
                    current_step_id = ?,
                    version_no = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = ?,
                    terminal_reason = ?
                WHERE workflow_id = ? AND version_no = ?
                """,
                (
                    state,
                    current_step_id,
                    next_state.current_version,
                    completed_at,
                    terminal_reason,
                    workflow_id,
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                fresh = self.get_workflow(workflow_id)
                if fresh is None:
                    raise LookupError(f"workflow not found: {workflow_id}")
                raise StaleVersionError(
                    expected_version=expected_version,
                    current_version=fresh.version_no,
                )

        updated = self.get_workflow(workflow_id)
        if updated is None:
            raise LookupError(f"workflow not found after update: {workflow_id}")
        return updated

    def append_transition(
        self,
        *,
        workflow_id: str,
        from_state: str,
        to_state: str,
        actor_type: str,
        actor_id: str,
        correlation_id: str,
        phase_name: str | None = None,
        transition_reason: str | None = None,
        causation_id: str | None = None,
        metadata_json: str = "{}",
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO core_workflow_transitions (
                    workflow_id,
                    from_state,
                    to_state,
                    phase_name,
                    transition_reason,
                    actor_type,
                    actor_id,
                    correlation_id,
                    causation_id,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    from_state,
                    to_state,
                    phase_name,
                    transition_reason,
                    actor_type,
                    actor_id,
                    correlation_id,
                    causation_id,
                    metadata_json,
                ),
            )
            return int(cursor.lastrowid)

    def create_incident(
        self,
        *,
        incident_id: str,
        severity: str,
        state: str,
        alert_type: str,
        source: str,
        summary: str,
        recommended_action: str | None = None,
        metadata_json: str = "{}",
    ) -> IncidentRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO core_incidents (
                    incident_id,
                    severity,
                    state,
                    alert_type,
                    source,
                    summary,
                    recommended_action,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    severity,
                    state,
                    alert_type,
                    source,
                    summary,
                    recommended_action,
                    metadata_json,
                ),
            )

        record = self.get_incident(incident_id)
        if record is None:
            raise LookupError(f"incident not found after create: {incident_id}")
        return record

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_incidents WHERE incident_id = ?",
                (incident_id,),
            ).fetchone()
        if row is None:
            return None
        return IncidentRecord(**dict(row))

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> WorkflowRecord:
        payload: dict[str, Any] = dict(row)
        return WorkflowRecord(**payload)

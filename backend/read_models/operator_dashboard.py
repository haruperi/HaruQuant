"""Denormalized operator dashboard read model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class OperatorDashboardReadModel:
    workflow_count: int
    open_incident_count: int
    pending_approval_count: int


@dataclass(frozen=True)
class WorkflowTrajectoryStep:
    step_id: str
    step_order: int
    step_type: str
    status: str
    assigned_agent: str | None
    input_ref: str | None
    output_ref: str | None
    latency_ms: int | None


@dataclass(frozen=True)
class WorkflowTrajectoryLogEntry:
    log_id: str
    agent_name: str
    phase: str
    iteration_no: int
    input_schema: str
    output_schema: str
    final_state: str
    latency_ms: int
    artifact_ref: str | None


@dataclass(frozen=True)
class WorkflowTrajectoryReadModel:
    workflow_id: str
    state: str
    current_step_id: str | None
    steps: tuple[WorkflowTrajectoryStep, ...]
    trajectory_logs: tuple[WorkflowTrajectoryLogEntry, ...]
    evaluation_reports: tuple[dict[str, Any], ...]


def build_operator_dashboard_read_model(db_path: str | Path) -> OperatorDashboardReadModel:
    """Build a small denormalized count view for dashboard hot paths."""

    connection = sqlite3.connect(str(db_path))
    try:
        workflow_count = connection.execute("SELECT COUNT(*) FROM core_workflows").fetchone()[0]
        open_incident_count = connection.execute(
            "SELECT COUNT(*) FROM core_incidents WHERE state = 'OPEN'"
        ).fetchone()[0]
        pending_approval_count = connection.execute(
            "SELECT COUNT(*) FROM gov_approvals WHERE state IN ('PENDING', 'OPEN')"
        ).fetchone()[0]
    finally:
        connection.close()
    return OperatorDashboardReadModel(
        workflow_count=int(workflow_count),
        open_incident_count=int(open_incident_count),
        pending_approval_count=int(pending_approval_count),
    )


def build_workflow_trajectory_read_model(
    db_path: str | Path,
    *,
    workflow_id: str,
) -> WorkflowTrajectoryReadModel:
    """Build an inspectable workflow execution trajectory."""

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        workflow = connection.execute(
            "SELECT workflow_id, state, current_step_id FROM core_workflows WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        if workflow is None:
            raise LookupError(f"workflow not found: {workflow_id}")

        step_rows = connection.execute(
            """
            SELECT step_id, step_order, step_type, status, assigned_agent,
                   input_ref, output_ref, latency_ms
            FROM core_workflow_steps
            WHERE workflow_id = ?
            ORDER BY step_order ASC
            """,
            (workflow_id,),
        ).fetchall()
        log_rows = connection.execute(
            """
            SELECT log_id, agent_name, phase, iteration_no, input_schema,
                   output_schema, final_state, latency_ms, artifact_ref
            FROM audit_trajectory_logs
            WHERE workflow_id = ?
            ORDER BY created_at ASC, log_id ASC
            """,
            (workflow_id,),
        ).fetchall()
        evaluation_rows = connection.execute(
            """
            SELECT evaluation_id, target_type, target_ref, rubric_name,
                   overall_score, verdict, created_at
            FROM core_evaluation_reports
            WHERE workflow_id = ?
            ORDER BY created_at ASC, evaluation_id ASC
            """,
            (workflow_id,),
        ).fetchall()
    finally:
        connection.close()

    return WorkflowTrajectoryReadModel(
        workflow_id=str(workflow["workflow_id"]),
        state=str(workflow["state"]),
        current_step_id=workflow["current_step_id"],
        steps=tuple(WorkflowTrajectoryStep(**dict(row)) for row in step_rows),
        trajectory_logs=tuple(
            WorkflowTrajectoryLogEntry(**dict(row)) for row in log_rows
        ),
        evaluation_reports=tuple(dict(row) for row in evaluation_rows),
    )

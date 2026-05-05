"""Workflow state persistence and resume.

Persists workflow execution state to SQLite so workflows can be
paused, resumed, and replayed after failures.
"""

from __future__ import annotations

from haruquant.utils import logger
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class WorkflowCheckpoint:
    """Saved state at a workflow step boundary."""
    workflow_id: str
    step_name: str
    step_index: int
    state_json: str
    output_payload: str
    final_state: str
    created_at: str  # ISO timestamp
    workflow_pattern: str = ""


class WorkflowStateManager:
    """Manages workflow execution state persistence to SQLite.

    Supports:
    - save_checkpoint: save state after each step
    - load_checkpoint: load last checkpoint for a workflow
    - load_checkpoints: load all checkpoints for a workflow
    - delete_checkpoints: clear checkpoints for a workflow

    Usage:
        mgr = WorkflowStateManager()
        mgr.save_checkpoint("wf-001", "step_1", 0, state_dict, output_dict, "COMPLETED")
        checkpoint = mgr.load_checkpoint("wf-001")
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or os.path.join(
            "backend", "data", "database", "sqlite", "workflow_states.db"
        )
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the database and table if they don't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    output_payload TEXT NOT NULL,
                    final_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    workflow_pattern TEXT DEFAULT '',
                    UNIQUE(workflow_id, step_index)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_workflow
                ON workflow_checkpoints(workflow_id, step_index)
            """)
            conn.commit()
        finally:
            conn.close()

    def save_checkpoint(
        self,
        workflow_id: str,
        step_name: str,
        step_index: int,
        state: Dict[str, Any],
        output_payload: Dict[str, Any],
        final_state: str,
        workflow_pattern: str = "",
    ) -> WorkflowCheckpoint:
        """Save a checkpoint after a workflow step completes."""
        now = datetime.now(timezone.utc).isoformat()
        checkpoint = WorkflowCheckpoint(
            workflow_id=workflow_id,
            step_name=step_name,
            step_index=step_index,
            state_json=json.dumps(state, default=str),
            output_payload=json.dumps(output_payload, default=str),
            final_state=final_state,
            created_at=now,
            workflow_pattern=workflow_pattern,
        )

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO workflow_checkpoints
                   (workflow_id, step_name, step_index, state_json,
                    output_payload, final_state, created_at, workflow_pattern)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    checkpoint.workflow_id,
                    checkpoint.step_name,
                    checkpoint.step_index,
                    checkpoint.state_json,
                    checkpoint.output_payload,
                    checkpoint.final_state,
                    checkpoint.created_at,
                    checkpoint.workflow_pattern,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return checkpoint

    def load_checkpoint(self, workflow_id: str) -> Optional[WorkflowCheckpoint]:
        """Load the most recent checkpoint for a workflow."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT * FROM workflow_checkpoints
                   WHERE workflow_id = ?
                   ORDER BY step_index DESC
                   LIMIT 1""",
                (workflow_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return WorkflowCheckpoint(
            workflow_id=row["workflow_id"],
            step_name=row["step_name"],
            step_index=row["step_index"],
            state_json=row["state_json"],
            output_payload=row["output_payload"],
            final_state=row["final_state"],
            created_at=row["created_at"],
            workflow_pattern=row["workflow_pattern"],
        )

    def load_checkpoints(self, workflow_id: str) -> List[WorkflowCheckpoint]:
        """Load all checkpoints for a workflow, ordered by step_index."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM workflow_checkpoints
                   WHERE workflow_id = ?
                   ORDER BY step_index ASC""",
                (workflow_id,),
            ).fetchall()
        finally:
            conn.close()

        return [
            WorkflowCheckpoint(
                workflow_id=row["workflow_id"],
                step_name=row["step_name"],
                step_index=row["step_index"],
                state_json=row["state_json"],
                output_payload=row["output_payload"],
                final_state=row["final_state"],
                created_at=row["created_at"],
                workflow_pattern=row["workflow_pattern"],
            )
            for row in rows
        ]

    def delete_checkpoints(self, workflow_id: str) -> int:
        """Delete all checkpoints for a workflow. Returns count deleted."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM workflow_checkpoints WHERE workflow_id = ?",
                (workflow_id,),
            )
            count = cursor.rowcount
            conn.commit()
            return count
        finally:
            conn.close()

    def get_execution_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get execution history as list of dicts for inspection."""
        checkpoints = self.load_checkpoints(workflow_id)
        return [
            {
                "step_name": cp.step_name,
                "step_index": cp.step_index,
                "final_state": cp.final_state,
                "created_at": cp.created_at,
                "output": json.loads(cp.output_payload),
                "state": json.loads(cp.state_json),
            }
            for cp in checkpoints
        ]

    def resume_from_checkpoint(
        self,
        workflow_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load the last checkpoint and return state for resume.

        Returns None if no checkpoint exists (start from beginning).
        """
        checkpoint = self.load_checkpoint(workflow_id)
        if checkpoint is None:
            return None

        return {
            "last_completed_step": checkpoint.step_name,
            "last_step_index": checkpoint.step_index,
            "last_output": json.loads(checkpoint.output_payload),
            "last_state": json.loads(checkpoint.state_json),
            "final_state": checkpoint.final_state,
        }

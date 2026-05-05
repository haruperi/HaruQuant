"""Repository for Agentic Firm Phase 4 persistence tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class AgentTaskRecord:
    task_id: str
    parent_task_id: str | None
    workflow_id: str | None
    title: str
    description: str
    owner_agent: str
    status: str
    priority: int
    expected_output_contract: str | None
    required_tools_json: str
    input_refs_json: str
    metadata_json: str
    created_at: str
    updated_at: str
    due_at: str | None


@dataclass(frozen=True)
class AgentTaskEventRecord:
    event_id: int
    task_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    actor_type: str
    actor_id: str
    event_payload_json: str
    created_at: str


@dataclass(frozen=True)
class EvidenceRefRecord:
    evidence_id: str
    evidence_type: str
    workflow_id: str | None
    task_id: str | None
    source_table: str | None
    source_ref_id: str | None
    uri: str | None
    content_hash: str | None
    summary: str | None
    source_agent: str | None
    metadata_json: str
    created_at: str


@dataclass(frozen=True)
class AuditLogRecord:
    audit_id: str
    actor_name: str
    agent_name: str | None
    tool_name: str | None
    action_type: str
    target_type: str | None
    target_ref_id: str | None
    input_hash: str
    output_hash: str | None
    evidence_refs_json: str
    request_id: str | None
    parent_task_id: str | None
    workflow_id: str | None
    metadata_json: str
    created_at: str


class AgenticFirmRepository:
    """Persistence wrapper for Phase 4 firm tables."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_agent_task(
        self,
        *,
        task_id: str,
        title: str,
        description: str,
        owner_agent: str,
        status: str = "pending",
        parent_task_id: str | None = None,
        workflow_id: str | None = None,
        priority: int = 3,
        expected_output_contract: str | None = None,
        required_tools_json: str = "[]",
        input_refs_json: str = "[]",
        metadata_json: str = "{}",
        due_at: str | None = None,
    ) -> AgentTaskRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_tasks (
                    task_id,
                    parent_task_id,
                    workflow_id,
                    title,
                    description,
                    owner_agent,
                    status,
                    priority,
                    expected_output_contract,
                    required_tools_json,
                    input_refs_json,
                    metadata_json,
                    due_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    parent_task_id,
                    workflow_id,
                    title,
                    description,
                    owner_agent,
                    status,
                    priority,
                    expected_output_contract,
                    required_tools_json,
                    input_refs_json,
                    metadata_json,
                    due_at,
                ),
            )

        record = self.get_agent_task(task_id)
        if record is None:
            raise LookupError(f"agent task not found after create: {task_id}")
        return record

    def get_agent_task(self, task_id: str) -> AgentTaskRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentTaskRecord(**dict(row))

    def append_agent_task_event(
        self,
        *,
        task_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str,
        from_status: str | None = None,
        to_status: str | None = None,
        event_payload_json: str = "{}",
    ) -> AgentTaskEventRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_task_events (
                    task_id,
                    event_type,
                    from_status,
                    to_status,
                    actor_type,
                    actor_id,
                    event_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    event_type,
                    from_status,
                    to_status,
                    actor_type,
                    actor_id,
                    event_payload_json,
                ),
            )
            event_id = int(cursor.lastrowid)

        record = self.get_agent_task_event(event_id)
        if record is None:
            raise LookupError(f"agent task event not found after create: {event_id}")
        return record

    def get_agent_task_event(self, event_id: int) -> AgentTaskEventRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_task_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentTaskEventRecord(**dict(row))

    def create_evidence_ref(
        self,
        *,
        evidence_id: str,
        evidence_type: str,
        workflow_id: str | None = None,
        task_id: str | None = None,
        source_table: str | None = None,
        source_ref_id: str | None = None,
        uri: str | None = None,
        content_hash: str | None = None,
        summary: str | None = None,
        source_agent: str | None = None,
        metadata_json: str = "{}",
    ) -> EvidenceRefRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_refs (
                    evidence_id,
                    evidence_type,
                    workflow_id,
                    task_id,
                    source_table,
                    source_ref_id,
                    uri,
                    content_hash,
                    summary,
                    source_agent,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    evidence_type,
                    workflow_id,
                    task_id,
                    source_table,
                    source_ref_id,
                    uri,
                    content_hash,
                    summary,
                    source_agent,
                    metadata_json,
                ),
            )

        record = self.get_evidence_ref(evidence_id)
        if record is None:
            raise LookupError(f"evidence ref not found after create: {evidence_id}")
        return record

    def get_evidence_ref(self, evidence_id: str) -> EvidenceRefRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence_refs WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        if row is None:
            return None
        return EvidenceRefRecord(**dict(row))

    def append_audit_log(
        self,
        *,
        audit_id: str,
        actor_name: str,
        action_type: str,
        input_hash: str,
        agent_name: str | None = None,
        tool_name: str | None = None,
        target_type: str | None = None,
        target_ref_id: str | None = None,
        output_hash: str | None = None,
        evidence_refs_json: str = "[]",
        request_id: str | None = None,
        parent_task_id: str | None = None,
        workflow_id: str | None = None,
        metadata_json: str = "{}",
    ) -> AuditLogRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_log (
                    audit_id,
                    actor_name,
                    agent_name,
                    tool_name,
                    action_type,
                    target_type,
                    target_ref_id,
                    input_hash,
                    output_hash,
                    evidence_refs_json,
                    request_id,
                    parent_task_id,
                    workflow_id,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    actor_name,
                    agent_name,
                    tool_name,
                    action_type,
                    target_type,
                    target_ref_id,
                    input_hash,
                    output_hash,
                    evidence_refs_json,
                    request_id,
                    parent_task_id,
                    workflow_id,
                    metadata_json,
                ),
            )

        record = self.get_audit_log(audit_id)
        if record is None:
            raise LookupError(f"audit log not found after append: {audit_id}")
        return record

    def get_audit_log(self, audit_id: str) -> AuditLogRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_log WHERE audit_id = ?",
                (audit_id,),
            ).fetchone()
        if row is None:
            return None
        return AuditLogRecord(**dict(row))


__all__ = [
    "AgentTaskEventRecord",
    "AgentTaskRecord",
    "AgenticFirmRepository",
    "AuditLogRecord",
    "EvidenceRefRecord",
]

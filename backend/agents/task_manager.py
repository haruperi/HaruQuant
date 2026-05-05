"""Task management for the HaruQuant Agentic Firm control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.data.database.repositories.agentic_firm_repository import (
    AgentTaskRecord,
    AgenticFirmRepository,
)


VALID_TASK_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("assigned", "blocked", "cancelled"),
    "assigned": ("running", "blocked", "cancelled"),
    "running": ("completed", "failed", "blocked", "cancelled"),
    "blocked": ("assigned", "failed", "cancelled"),
    "completed": (),
    "failed": (),
    "cancelled": (),
}


@dataclass(frozen=True)
class TaskTreeNode:
    """A task plus recursively nested children."""

    task: AgentTaskRecord
    children: tuple["TaskTreeNode", ...] = ()


@dataclass
class MemoryTaskRecord:
    """In-memory fallback used by tests or callers without a database."""

    task_id: str
    parent_task_id: str | None
    workflow_id: str | None
    title: str
    description: str
    owner_agent: str
    status: str
    priority: int
    expected_output_contract: str | None
    required_tools_json: str = "[]"
    input_refs_json: str = "[]"
    metadata_json: str = "{}"
    created_at: str = field(default_factory=lambda: _utc_now_iso())
    updated_at: str = field(default_factory=lambda: _utc_now_iso())
    due_at: str | None = None


class AgentTaskTransitionError(ValueError):
    """Raised when a task status transition violates the firm state machine."""


class AgentTaskManager:
    """Create, assign, transition, and inspect firm task trees."""

    def __init__(
        self,
        *,
        repository: AgenticFirmRepository | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        if repository is not None and db_path is not None:
            raise ValueError("pass either repository or db_path, not both")
        self.repository = repository or (AgenticFirmRepository(db_path) if db_path else None)
        self._memory_tasks: dict[str, MemoryTaskRecord] = {}
        self._memory_events: list[dict[str, Any]] = []

    def create_task(
        self,
        *,
        title: str,
        description: str,
        owner_agent: str,
        workflow_id: str | None = None,
        parent_task_id: str | None = None,
        task_id: str | None = None,
        priority: int = 3,
        expected_output_contract: str | None = None,
        required_tools: tuple[str, ...] = (),
        input_refs: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> AgentTaskRecord:
        task_id = task_id or f"task-{uuid4().hex}"
        metadata_json = json.dumps(metadata or {}, sort_keys=True)
        required_tools_json = json.dumps(list(required_tools), sort_keys=True)
        input_refs_json = json.dumps(list(input_refs), sort_keys=True)

        if self.repository is not None:
            task = self.repository.create_agent_task(
                task_id=task_id,
                workflow_id=workflow_id,
                parent_task_id=parent_task_id,
                title=title,
                description=description,
                owner_agent=owner_agent,
                priority=priority,
                expected_output_contract=expected_output_contract,
                required_tools_json=required_tools_json,
                input_refs_json=input_refs_json,
                metadata_json=metadata_json,
            )
            self._append_event(
                task_id=task.task_id,
                event_type="created",
                actor_type="system",
                actor_id="agent_task_manager",
                to_status=task.status,
            )
            return task

        task = MemoryTaskRecord(
            task_id=task_id,
            parent_task_id=parent_task_id,
            workflow_id=workflow_id,
            title=title,
            description=description,
            owner_agent=owner_agent,
            status="pending",
            priority=priority,
            expected_output_contract=expected_output_contract,
            required_tools_json=required_tools_json,
            input_refs_json=input_refs_json,
            metadata_json=metadata_json,
        )
        self._memory_tasks[task_id] = task
        self._append_event(
            task_id=task.task_id,
            event_type="created",
            actor_type="system",
            actor_id="agent_task_manager",
            to_status=task.status,
        )
        return self._to_record(task)

    def create_child_task(self, *, parent_task_id: str, **kwargs: Any) -> AgentTaskRecord:
        parent = self.require_task(parent_task_id)
        kwargs.setdefault("workflow_id", parent.workflow_id)
        kwargs["parent_task_id"] = parent_task_id
        return self.create_task(**kwargs)

    def assign_task(self, task_id: str, *, owner_agent: str, actor_id: str = "planner") -> AgentTaskRecord:
        return self._transition_task(
            task_id,
            to_status="assigned",
            event_type="assigned",
            actor_id=actor_id,
            owner_agent=owner_agent,
        )

    def start_task(self, task_id: str, *, actor_id: str) -> AgentTaskRecord:
        return self._transition_task(
            task_id,
            to_status="running",
            event_type="started",
            actor_id=actor_id,
        )

    def complete_task(
        self,
        task_id: str,
        *,
        actor_id: str,
        output: dict[str, Any] | None = None,
    ) -> AgentTaskRecord:
        return self._transition_task(
            task_id,
            to_status="completed",
            event_type="completed",
            actor_id=actor_id,
            event_payload=output or {},
        )

    def fail_task(self, task_id: str, *, actor_id: str, reason: str) -> AgentTaskRecord:
        return self._transition_task(
            task_id,
            to_status="failed",
            event_type="failed",
            actor_id=actor_id,
            event_payload={"reason": reason},
        )

    def block_task(self, task_id: str, *, actor_id: str, reason: str) -> AgentTaskRecord:
        return self._transition_task(
            task_id,
            to_status="blocked",
            event_type="blocked",
            actor_id=actor_id,
            event_payload={"reason": reason},
        )

    def get_task_tree(self, root_task_id: str) -> TaskTreeNode:
        root = self.require_task(root_task_id)
        return TaskTreeNode(
            task=root,
            children=tuple(self.get_task_tree(child.task_id) for child in self._children_of(root_task_id)),
        )

    def get_task(self, task_id: str) -> AgentTaskRecord | None:
        if self.repository is not None:
            return self.repository.get_agent_task(task_id)
        task = self._memory_tasks.get(task_id)
        return self._to_record(task) if task is not None else None

    def require_task(self, task_id: str) -> AgentTaskRecord:
        task = self.get_task(task_id)
        if task is None:
            raise LookupError(f"agent task not found: {task_id}")
        return task

    def _transition_task(
        self,
        task_id: str,
        *,
        to_status: str,
        event_type: str,
        actor_id: str,
        owner_agent: str | None = None,
        event_payload: dict[str, Any] | None = None,
    ) -> AgentTaskRecord:
        task = self.require_task(task_id)
        allowed = VALID_TASK_TRANSITIONS.get(task.status, ())
        if to_status not in allowed:
            raise AgentTaskTransitionError(
                f"invalid task transition for {task_id}: {task.status} -> {to_status}"
            )

        if self.repository is not None:
            with self.repository._connect() as connection:  # noqa: SLF001
                connection.execute(
                    """
                    UPDATE agent_tasks
                    SET status = ?,
                        owner_agent = COALESCE(?, owner_agent),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                    """,
                    (to_status, owner_agent, task_id),
                )
        else:
            memory_task = self._memory_tasks[task_id]
            memory_task.status = to_status
            if owner_agent is not None:
                memory_task.owner_agent = owner_agent
            memory_task.updated_at = _utc_now_iso()

        self._append_event(
            task_id=task_id,
            event_type=event_type,
            actor_type="agent",
            actor_id=actor_id,
            from_status=task.status,
            to_status=to_status,
            event_payload=event_payload or {},
        )
        return self.require_task(task_id)

    def _append_event(
        self,
        *,
        task_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str,
        from_status: str | None = None,
        to_status: str | None = None,
        event_payload: dict[str, Any] | None = None,
    ) -> None:
        payload_json = json.dumps(event_payload or {}, sort_keys=True)
        if self.repository is not None:
            self.repository.append_agent_task_event(
                task_id=task_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                from_status=from_status,
                to_status=to_status,
                event_payload_json=payload_json,
            )
            return
        self._memory_events.append(
            {
                "task_id": task_id,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "from_status": from_status,
                "to_status": to_status,
                "event_payload_json": payload_json,
                "created_at": _utc_now_iso(),
            }
        )

    def _children_of(self, parent_task_id: str) -> tuple[AgentTaskRecord, ...]:
        if self.repository is not None:
            with self.repository._connect() as connection:  # noqa: SLF001
                rows = connection.execute(
                    """
                    SELECT * FROM agent_tasks
                    WHERE parent_task_id = ?
                    ORDER BY created_at, task_id
                    """,
                    (parent_task_id,),
                ).fetchall()
            return tuple(AgentTaskRecord(**dict(row)) for row in rows)
        children = [
            self._to_record(task)
            for task in self._memory_tasks.values()
            if task.parent_task_id == parent_task_id
        ]
        return tuple(sorted(children, key=lambda task: (task.created_at, task.task_id)))

    @staticmethod
    def _to_record(task: MemoryTaskRecord) -> AgentTaskRecord:
        return AgentTaskRecord(**asdict(task))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "AgentTaskManager",
    "AgentTaskTransitionError",
    "TaskTreeNode",
    "VALID_TASK_TRANSITIONS",
]

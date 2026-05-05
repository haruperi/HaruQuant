"""Task manager for agentic firm task trees."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from data.database.repositories.agentic_firm_repository import AgenticFirmRepository


class AgentTaskTransitionError(ValueError):
    """Raised when a task status transition is invalid."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ManagedAgentTask:
    task_id: str
    parent_task_id: str | None
    workflow_id: str | None
    title: str
    description: str
    owner_agent: str
    status: str
    priority: int = 3
    expected_output_contract: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentTaskTree:
    task: ManagedAgentTask
    children: list["AgentTaskTree"] = field(default_factory=list)


_ALLOWED_TRANSITIONS = {
    "pending": {"assigned", "running", "blocked", "cancelled"},
    "assigned": {"running", "blocked", "cancelled"},
    "running": {"completed", "failed", "blocked", "cancelled"},
    "blocked": {"assigned", "running", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class AgentTaskManager:
    """Manages in-memory or persisted agent task trees."""

    def __init__(self, repository: AgenticFirmRepository | None = None) -> None:
        self.repository = repository
        self._tasks: dict[str, ManagedAgentTask] = {}

    def create_task(
        self,
        *,
        title: str,
        description: str,
        owner_agent: str,
        parent_task_id: str | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
        status: str = "pending",
        priority: int = 3,
        expected_output_contract: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ManagedAgentTask:
        task = ManagedAgentTask(
            task_id=task_id or f"task-{uuid4().hex}",
            parent_task_id=parent_task_id,
            workflow_id=workflow_id,
            title=title,
            description=description,
            owner_agent=owner_agent,
            status=status,
            priority=priority,
            expected_output_contract=expected_output_contract,
            metadata=metadata or {},
        )
        self._tasks[task.task_id] = task
        if self.repository is not None:
            self.repository.create_agent_task(
                task_id=task.task_id,
                parent_task_id=task.parent_task_id,
                workflow_id=task.workflow_id,
                title=task.title,
                description=task.description,
                owner_agent=task.owner_agent,
                status=task.status,
                priority=task.priority,
                expected_output_contract=task.expected_output_contract,
                metadata_json="{}",
            )
            self.repository.append_agent_task_event(
                task_id=task.task_id,
                event_type="created",
                actor_type="system",
                actor_id="task_manager",
                to_status=task.status,
            )
        return task

    def create_child_task(self, *, parent_task_id: str, **kwargs: Any) -> ManagedAgentTask:
        if parent_task_id not in self._tasks and self.get_task(parent_task_id) is None:
            raise KeyError(f"Unknown parent task: {parent_task_id}")
        return self.create_task(parent_task_id=parent_task_id, **kwargs)

    def get_task(self, task_id: str) -> ManagedAgentTask | None:
        task = self._tasks.get(task_id)
        if task is not None:
            return task
        if self.repository is None:
            return None
        record = self.repository.get_agent_task(task_id)
        if record is None:
            return None
        task = ManagedAgentTask(
            task_id=record.task_id,
            parent_task_id=record.parent_task_id,
            workflow_id=record.workflow_id,
            title=record.title,
            description=record.description,
            owner_agent=record.owner_agent,
            status=record.status,
            priority=record.priority,
            expected_output_contract=record.expected_output_contract,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        self._tasks[task_id] = task
        return task

    def assign_task(self, task_id: str, *, owner_agent: str) -> ManagedAgentTask:
        return self._transition(
            task_id,
            to_status="assigned",
            actor_id=owner_agent,
            owner_agent=owner_agent,
        )

    def start_task(self, task_id: str, *, actor_id: str) -> ManagedAgentTask:
        return self._transition(task_id, to_status="running", actor_id=actor_id)

    def complete_task(self, task_id: str, *, actor_id: str) -> ManagedAgentTask:
        return self._transition(task_id, to_status="completed", actor_id=actor_id)

    def fail_task(self, task_id: str, *, actor_id: str) -> ManagedAgentTask:
        return self._transition(task_id, to_status="failed", actor_id=actor_id)

    def block_task(self, task_id: str, *, actor_id: str) -> ManagedAgentTask:
        return self._transition(task_id, to_status="blocked", actor_id=actor_id)

    def get_task_tree(self, task_id: str) -> AgentTaskTree:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Unknown task: {task_id}")
        children = [
            self.get_task_tree(child.task_id)
            for child in self._tasks.values()
            if child.parent_task_id == task_id
        ]
        return AgentTaskTree(task=task, children=children)

    def _transition(
        self,
        task_id: str,
        *,
        to_status: str,
        actor_id: str,
        owner_agent: str | None = None,
    ) -> ManagedAgentTask:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Unknown task: {task_id}")
        if to_status not in _ALLOWED_TRANSITIONS.get(task.status, set()):
            raise AgentTaskTransitionError(
                f"Cannot transition task {task_id} from {task.status} to {to_status}"
            )
        updated = ManagedAgentTask(
            task_id=task.task_id,
            parent_task_id=task.parent_task_id,
            workflow_id=task.workflow_id,
            title=task.title,
            description=task.description,
            owner_agent=owner_agent or task.owner_agent,
            status=to_status,
            priority=task.priority,
            expected_output_contract=task.expected_output_contract,
            created_at=task.created_at,
            updated_at=_now(),
            metadata=task.metadata,
        )
        self._tasks[task_id] = updated
        if self.repository is not None:
            with self.repository._connect() as connection:  # noqa: SLF001
                connection.execute(
                    """
                    UPDATE agent_tasks
                    SET status = ?, owner_agent = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                    """,
                    (updated.status, updated.owner_agent, task_id),
                )
            self.repository.append_agent_task_event(
                task_id=task_id,
                event_type="status_transition",
                actor_type="agent",
                actor_id=actor_id,
                from_status=task.status,
                to_status=to_status,
            )
        return updated


__all__ = [
    "AgentTaskManager",
    "AgentTaskTransitionError",
    "AgentTaskTree",
    "ManagedAgentTask",
]

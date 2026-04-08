"""Workflow persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.db import WorkflowRepository

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

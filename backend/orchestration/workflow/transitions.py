"""Deterministic workflow transition maps."""

from __future__ import annotations

from services.utils.logger import logger
from .states import WorkflowState


WORKFLOW_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.CREATED: frozenset(
        {
            WorkflowState.REASONING,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.REASONING: frozenset(
        {
            WorkflowState.PLANNING,
            WorkflowState.BLOCKED_BY_POLICY,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.PLANNING: frozenset(
        {
            WorkflowState.ACTING,
            WorkflowState.BLOCKED_BY_POLICY,
            WorkflowState.BLOCKED_BY_RISK,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.ACTING: frozenset(
        {
            WorkflowState.OBSERVING,
            WorkflowState.RECONCILING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.OBSERVING: frozenset(
        {
            WorkflowState.EVALUATING,
            WorkflowState.RECONCILING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.EVALUATING: frozenset(
        {
            WorkflowState.REFINING,
            WorkflowState.COMPLETED,
            WorkflowState.BLOCKED_BY_RISK,
            WorkflowState.BLOCKED_BY_POLICY,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.REFINING: frozenset(
        {
            WorkflowState.REASONING,
            WorkflowState.PLANNING,
            WorkflowState.COMPLETED,
            WorkflowState.BLOCKED_BY_POLICY,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.BLOCKED_BY_RISK: frozenset(
        {
            WorkflowState.REASONING,
            WorkflowState.PLANNING,
            WorkflowState.CANCELLED,
            WorkflowState.FAILED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.BLOCKED_BY_POLICY: frozenset(
        {
            WorkflowState.REASONING,
            WorkflowState.PLANNING,
            WorkflowState.CANCELLED,
            WorkflowState.FAILED,
            WorkflowState.TIMED_OUT,
        }
    ),
    WorkflowState.RECONCILING: frozenset(
        {
            WorkflowState.OBSERVING,
            WorkflowState.EVALUATING,
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.COMPLETED: frozenset(),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.CANCELLED: frozenset(),
    WorkflowState.TIMED_OUT: frozenset(),
}


def is_allowed_workflow_transition(
    from_state: WorkflowState,
    to_state: WorkflowState,
) -> bool:
    """Return whether a workflow state transition is allowed."""

    return to_state in WORKFLOW_TRANSITIONS[from_state]

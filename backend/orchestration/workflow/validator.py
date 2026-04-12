"""Workflow FSM validation service."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common import PolicyError

from .states import WorkflowState
from .transitions import is_allowed_workflow_transition


@dataclass(frozen=True)
class WorkflowValidationContext:
    """Observed workflow execution context needed for completion validation."""

    observe_seen: bool = False
    evaluate_seen: bool = False
    emergency_exit_policy: bool = False


class WorkflowStateValidationError(PolicyError):
    """Raised when a workflow transition violates the deterministic FSM."""

    def __init__(self, code: str, message: str, **details: object) -> None:
        super().__init__(code, message, details=details)


class WorkflowStateValidator:
    """Deterministic validator for workflow state transitions."""

    def validate_transition(
        self,
        *,
        from_state: WorkflowState,
        to_state: WorkflowState,
        context: WorkflowValidationContext | None = None,
    ) -> None:
        validation_context = context or WorkflowValidationContext()

        if not is_allowed_workflow_transition(from_state, to_state):
            raise WorkflowStateValidationError(
                "workflow_transition_not_allowed",
                "Workflow state transition is not allowed.",
                from_state=from_state.value,
                to_state=to_state.value,
            )

        if to_state is WorkflowState.COMPLETED:
            self._validate_completion_requirements(validation_context)

    @staticmethod
    def _validate_completion_requirements(context: WorkflowValidationContext) -> None:
        if context.emergency_exit_policy:
            # Emergency paths may defer evaluation, but must still observe post-action.
            if not context.observe_seen:
                raise WorkflowStateValidationError(
                    "workflow_completion_missing_observe",
                    "Emergency workflow completion still requires an observation phase.",
                    observe_seen=context.observe_seen,
                    evaluate_seen=context.evaluate_seen,
                    emergency_exit_policy=context.emergency_exit_policy,
                )
            return

        if not context.observe_seen or not context.evaluate_seen:
            raise WorkflowStateValidationError(
                "workflow_completion_missing_required_phases",
                "Workflow cannot complete before Observe and Evaluate have both occurred.",
                observe_seen=context.observe_seen,
                evaluate_seen=context.evaluate_seen,
                emergency_exit_policy=context.emergency_exit_policy,
            )

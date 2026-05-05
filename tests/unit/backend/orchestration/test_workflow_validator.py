from backend_retiring.orchestration.workflow import (
    WorkflowState,
    WorkflowStateValidationError,
    WorkflowStateValidator,
    WorkflowValidationContext,
)


def test_workflow_validator_rejects_completion_when_observe_or_evaluate_missing() -> None:
    validator = WorkflowStateValidator()

    failed = False
    try:
        validator.validate_transition(
            from_state=WorkflowState.EVALUATING,
            to_state=WorkflowState.COMPLETED,
            context=WorkflowValidationContext(observe_seen=True, evaluate_seen=False),
        )
    except WorkflowStateValidationError as exc:
        failed = exc.code == "workflow_completion_missing_required_phases"

    assert failed is True


def test_workflow_validator_allows_completion_when_required_phases_are_present() -> None:
    validator = WorkflowStateValidator()

    validator.validate_transition(
        from_state=WorkflowState.EVALUATING,
        to_state=WorkflowState.COMPLETED,
        context=WorkflowValidationContext(observe_seen=True, evaluate_seen=True),
    )


def test_workflow_validator_allows_emergency_completion_only_after_observe() -> None:
    validator = WorkflowStateValidator()

    validator.validate_transition(
        from_state=WorkflowState.RECONCILING,
        to_state=WorkflowState.COMPLETED,
        context=WorkflowValidationContext(
            observe_seen=True,
            evaluate_seen=False,
            emergency_exit_policy=True,
        ),
    )

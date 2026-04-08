from backend.orchestration.workflow import (
    WorkflowState,
    is_allowed_workflow_transition,
)


def test_workflow_transition_map_allows_required_forward_paths() -> None:
    assert is_allowed_workflow_transition(WorkflowState.CREATED, WorkflowState.REASONING)
    assert is_allowed_workflow_transition(WorkflowState.REASONING, WorkflowState.PLANNING)
    assert is_allowed_workflow_transition(WorkflowState.PLANNING, WorkflowState.ACTING)
    assert is_allowed_workflow_transition(WorkflowState.ACTING, WorkflowState.OBSERVING)
    assert is_allowed_workflow_transition(WorkflowState.OBSERVING, WorkflowState.EVALUATING)
    assert is_allowed_workflow_transition(WorkflowState.EVALUATING, WorkflowState.REFINING)
    assert is_allowed_workflow_transition(WorkflowState.EVALUATING, WorkflowState.COMPLETED)


def test_workflow_transition_map_rejects_invalid_or_terminal_transitions() -> None:
    assert not is_allowed_workflow_transition(WorkflowState.CREATED, WorkflowState.ACTING)
    assert not is_allowed_workflow_transition(WorkflowState.PLANNING, WorkflowState.COMPLETED)
    assert not is_allowed_workflow_transition(WorkflowState.COMPLETED, WorkflowState.REASONING)
    assert not is_allowed_workflow_transition(WorkflowState.FAILED, WorkflowState.RECONCILING)

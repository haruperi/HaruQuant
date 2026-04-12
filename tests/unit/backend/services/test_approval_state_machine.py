from backend.common import PolicyError
from backend.services.approval import ApprovalState, ApprovalStateMachine


def test_approval_state_machine_allows_expected_transitions() -> None:
    machine = ApprovalStateMachine()
    machine.validate(ApprovalState.PENDING, ApprovalState.PARTIALLY_APPROVED)
    machine.validate(ApprovalState.PARTIALLY_APPROVED, ApprovalState.APPROVED)


def test_approval_state_machine_rejects_invalid_transitions() -> None:
    machine = ApprovalStateMachine()

    failed = False
    try:
        machine.validate(ApprovalState.APPROVED, ApprovalState.PENDING)
    except PolicyError as exc:
        failed = exc.code == "approval_transition_not_allowed"

    assert failed is True

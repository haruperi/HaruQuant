from backend.orchestration.workflow import KillSwitchState
from backend.services import (
    KillSwitchService,
    KillSwitchStateMachine,
    KillSwitchTransitionError,
)


def test_kill_switch_state_machine_allows_governed_recovery_sequence() -> None:
    machine = KillSwitchStateMachine(state=KillSwitchState.ARMED)
    machine = machine.transition(target_state=KillSwitchState.SOFT_TRIGGERED)
    machine = machine.transition(
        target_state=KillSwitchState.RECOVERY_PENDING,
        authorization="risk_manager",
    )
    machine = machine.transition(
        target_state=KillSwitchState.RECOVERY_APPROVED,
        authorization="compliance",
    )
    machine = machine.transition(target_state=KillSwitchState.ARMED)

    assert machine.state == KillSwitchState.ARMED


def test_kill_switch_state_machine_rejects_unauthorized_recovery_transition() -> None:
    machine = KillSwitchStateMachine(state=KillSwitchState.HARD_TRIGGERED)

    try:
        machine.transition(target_state=KillSwitchState.RECOVERY_PENDING)
    except KillSwitchTransitionError as exc:
        assert "authorized actor" in str(exc)
    else:
        raise AssertionError("expected recovery authorization error")


def test_kill_switch_service_maps_action_to_target_state() -> None:
    service = KillSwitchService()

    result = service.apply_action(
        current_state=KillSwitchState.SOFT_TRIGGERED,
        action="request_recovery",
        authorization="operator",
    )

    assert result.state == KillSwitchState.RECOVERY_PENDING

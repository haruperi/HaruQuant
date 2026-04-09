from backend.orchestration.workflow import KillSwitchState
from backend.services import (
    KillSwitchBlockEvaluation,
    KillSwitchService,
    KillSwitchStateMachine,
    KillSwitchTransitionError,
    evaluate_new_entry_block,
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


def test_evaluate_new_entry_block_blocks_when_kill_switch_triggered() -> None:
    result = evaluate_new_entry_block(KillSwitchState.HARD_TRIGGERED)

    assert isinstance(result, KillSwitchBlockEvaluation)
    assert result.blocked is True
    assert result.allow_force_exit is True
    assert result.reason_codes == ("kill_switch_blocks_new_entries",)

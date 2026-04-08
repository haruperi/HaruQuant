from backend.orchestration.workflow import (
    KillSwitchState,
    is_allowed_kill_switch_transition,
)


def test_kill_switch_transition_map_allows_recovery_sequence() -> None:
    assert is_allowed_kill_switch_transition(KillSwitchState.ARMED, KillSwitchState.SOFT_TRIGGERED)
    assert is_allowed_kill_switch_transition(KillSwitchState.SOFT_TRIGGERED, KillSwitchState.RECOVERY_PENDING)
    assert is_allowed_kill_switch_transition(KillSwitchState.HARD_TRIGGERED, KillSwitchState.RECOVERY_PENDING)
    assert is_allowed_kill_switch_transition(KillSwitchState.RECOVERY_PENDING, KillSwitchState.RECOVERY_APPROVED)
    assert is_allowed_kill_switch_transition(KillSwitchState.RECOVERY_APPROVED, KillSwitchState.ARMED)


def test_kill_switch_transition_map_rejects_unauthorized_recovery_paths() -> None:
    assert not is_allowed_kill_switch_transition(KillSwitchState.SOFT_TRIGGERED, KillSwitchState.ARMED)
    assert not is_allowed_kill_switch_transition(KillSwitchState.HARD_TRIGGERED, KillSwitchState.ARMED)
    assert not is_allowed_kill_switch_transition(KillSwitchState.ARMED, KillSwitchState.RECOVERY_APPROVED)

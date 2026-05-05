"""Kill-switch transition rules."""

from __future__ import annotations

from .states import KillSwitchState


KILL_SWITCH_TRANSITIONS: dict[KillSwitchState, frozenset[KillSwitchState]] = {
    KillSwitchState.ARMED: frozenset(
        {
            KillSwitchState.SOFT_TRIGGERED,
            KillSwitchState.HARD_TRIGGERED,
        }
    ),
    KillSwitchState.SOFT_TRIGGERED: frozenset(
        {
            KillSwitchState.RECOVERY_PENDING,
            KillSwitchState.HARD_TRIGGERED,
        }
    ),
    KillSwitchState.HARD_TRIGGERED: frozenset(
        {
            KillSwitchState.RECOVERY_PENDING,
        }
    ),
    KillSwitchState.RECOVERY_PENDING: frozenset(
        {
            KillSwitchState.RECOVERY_APPROVED,
            KillSwitchState.HARD_TRIGGERED,
        }
    ),
    KillSwitchState.RECOVERY_APPROVED: frozenset(
        {
            KillSwitchState.ARMED,
            KillSwitchState.SOFT_TRIGGERED,
            KillSwitchState.HARD_TRIGGERED,
        }
    ),
}


def is_allowed_kill_switch_transition(
    from_state: KillSwitchState,
    to_state: KillSwitchState,
) -> bool:
    """Return whether a kill-switch state transition is allowed."""

    return to_state in KILL_SWITCH_TRANSITIONS[from_state]

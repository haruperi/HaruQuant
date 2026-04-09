"""Safety service primitives for kill-switch and hard-stop controls."""

from .kill_switch import (
    KillSwitchBlockEvaluation,
    KillSwitchAction,
    KillSwitchService,
    KillSwitchStateMachine,
    KillSwitchTransitionError,
    RecoveryAuthorization,
    evaluate_new_entry_block,
)

__all__ = [
    "KillSwitchBlockEvaluation",
    "KillSwitchAction",
    "KillSwitchService",
    "KillSwitchStateMachine",
    "KillSwitchTransitionError",
    "RecoveryAuthorization",
    "evaluate_new_entry_block",
]

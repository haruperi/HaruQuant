"""Safety service primitives for kill-switch and hard-stop controls."""

from .kill_switch import (
    KillSwitchBlockEvaluation,
    KillSwitchAction,
    KillSwitchService,
    KillSwitchStateMachine,
    KillSwitchTransitionError,
    RecoveryApproval,
    RecoveryAuthorization,
    evaluate_new_entry_block,
    require_hard_trigger_recovery_dual_auth,
)

__all__ = [
    "KillSwitchBlockEvaluation",
    "KillSwitchAction",
    "KillSwitchService",
    "KillSwitchStateMachine",
    "KillSwitchTransitionError",
    "RecoveryApproval",
    "RecoveryAuthorization",
    "evaluate_new_entry_block",
    "require_hard_trigger_recovery_dual_auth",
]

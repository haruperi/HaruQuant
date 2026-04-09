"""Safety service primitives for kill-switch and hard-stop controls."""

from .kill_switch import (
    KillSwitchAction,
    KillSwitchService,
    KillSwitchStateMachine,
    KillSwitchTransitionError,
    RecoveryAuthorization,
)

__all__ = [
    "KillSwitchAction",
    "KillSwitchService",
    "KillSwitchStateMachine",
    "KillSwitchTransitionError",
    "RecoveryAuthorization",
]

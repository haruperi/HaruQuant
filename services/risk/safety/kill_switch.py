"""Kill-switch domain model and governed state-machine helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from services.governance.workflow import (
    KillSwitchState,
    is_allowed_kill_switch_transition,
)


KillSwitchAction = Literal["soft_trigger", "hard_trigger", "request_recovery", "approve_recovery", "rearm"]
RecoveryAuthorization = Literal["operator", "risk_manager", "compliance"]


class KillSwitchTransitionError(ValueError):
    """Raised when a kill-switch transition is not authorized."""


@dataclass(frozen=True)
class KillSwitchBlockEvaluation:
    """Whether new live entries are blocked under the current kill-switch state."""

    blocked: bool
    allow_force_exit: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryApproval:
    """Approval attestation used for governed kill-switch recovery."""

    approver_role: RecoveryAuthorization
    approver_id: str


@dataclass(frozen=True)
class KillSwitchStateMachine:
    """Thin domain wrapper around the kill-switch transition map."""

    state: KillSwitchState

    def can_transition(self, target_state: KillSwitchState) -> bool:
        """Return whether the target state is allowed from the current state."""

        return is_allowed_kill_switch_transition(self.state, target_state)

    def transition(
        self,
        *,
        target_state: KillSwitchState,
        authorization: RecoveryAuthorization | None = None,
    ) -> "KillSwitchStateMachine":
        """Apply a governed transition and return the next state wrapper."""

        if not self.can_transition(target_state):
            raise KillSwitchTransitionError(
                f"kill-switch transition not allowed: {self.state.value} -> {target_state.value}"
            )

        if target_state in {KillSwitchState.RECOVERY_PENDING, KillSwitchState.RECOVERY_APPROVED}:
            if authorization not in {"operator", "risk_manager", "compliance"}:
                raise KillSwitchTransitionError("recovery transition requires authorized actor")

        if target_state == KillSwitchState.ARMED and self.state != KillSwitchState.RECOVERY_APPROVED:
            raise KillSwitchTransitionError("kill switch can only re-arm after recovery approval")

        return KillSwitchStateMachine(state=target_state)


class KillSwitchService:
    """Map domain actions to governed kill-switch state transitions."""

    ACTION_TARGETS: dict[KillSwitchAction, KillSwitchState] = {
        "soft_trigger": KillSwitchState.SOFT_TRIGGERED,
        "hard_trigger": KillSwitchState.HARD_TRIGGERED,
        "request_recovery": KillSwitchState.RECOVERY_PENDING,
        "approve_recovery": KillSwitchState.RECOVERY_APPROVED,
        "rearm": KillSwitchState.ARMED,
    }

    def apply_action(
        self,
        *,
        current_state: KillSwitchState,
        action: KillSwitchAction,
        authorization: RecoveryAuthorization | None = None,
    ) -> KillSwitchStateMachine:
        """Apply a named action to the current state and return the next state wrapper."""

        machine = KillSwitchStateMachine(state=current_state)
        return machine.transition(
            target_state=self.ACTION_TARGETS[action],
            authorization=authorization,
        )


def evaluate_new_entry_block(current_state: KillSwitchState) -> KillSwitchBlockEvaluation:
    """Globally block new live entries whenever the kill switch is not fully armed."""

    if current_state == KillSwitchState.ARMED:
        return KillSwitchBlockEvaluation(blocked=False, allow_force_exit=True)
    return KillSwitchBlockEvaluation(
        blocked=True,
        allow_force_exit=True,
        reason_codes=("kill_switch_blocks_new_entries",),
    )


def require_hard_trigger_recovery_dual_auth(
    approvals: tuple[RecoveryApproval, ...],
) -> bool:
    """Require distinct Risk Manager and Compliance approvals for hard recovery."""

    distinct_approvers = {approval.approver_id for approval in approvals}
    distinct_roles = {approval.approver_role for approval in approvals}
    return len(distinct_approvers) >= 2 and {"risk_manager", "compliance"}.issubset(
        distinct_roles
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

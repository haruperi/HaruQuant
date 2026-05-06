"""Canonical workflow state enums and transition guards."""

from __future__ import annotations

from enum import Enum


class ProposalState(str, Enum):
    DRAFT = "DRAFT"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    READY_FOR_RISK = "READY_FOR_RISK"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTION_PENDING = "EXECUTION_PENDING"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class KillSwitchState(str, Enum):
    ARMED = "ARMED"
    SOFT_TRIGGERED = "SOFT_TRIGGERED"
    HARD_TRIGGERED = "HARD_TRIGGERED"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RECOVERY_APPROVED = "RECOVERY_APPROVED"


_PROPOSAL_TRANSITIONS: dict[ProposalState, set[ProposalState]] = {
    ProposalState.DRAFT: {ProposalState.EVIDENCE_PENDING, ProposalState.REJECTED, ProposalState.CANCELLED},
    ProposalState.EVIDENCE_PENDING: {ProposalState.READY_FOR_RISK, ProposalState.REJECTED, ProposalState.CANCELLED},
    ProposalState.READY_FOR_RISK: {ProposalState.APPROVED, ProposalState.REJECTED},
    ProposalState.APPROVED: {ProposalState.EXECUTION_PENDING, ProposalState.CANCELLED},
    ProposalState.EXECUTION_PENDING: {ProposalState.SENT, ProposalState.EXECUTION_FAILED, ProposalState.CANCELLED},
    ProposalState.SENT: {ProposalState.ACKNOWLEDGED, ProposalState.EXECUTION_FAILED},
    ProposalState.ACKNOWLEDGED: {ProposalState.PARTIALLY_FILLED, ProposalState.FILLED, ProposalState.CLOSED},
    ProposalState.PARTIALLY_FILLED: {ProposalState.FILLED, ProposalState.CLOSED, ProposalState.EXECUTION_FAILED},
    ProposalState.FILLED: {ProposalState.CLOSED},
    ProposalState.REJECTED: set(),
    ProposalState.CLOSED: set(),
    ProposalState.CANCELLED: set(),
    ProposalState.EXECUTION_FAILED: set(),
}


_KILL_SWITCH_TRANSITIONS: dict[KillSwitchState, set[KillSwitchState]] = {
    KillSwitchState.ARMED: {KillSwitchState.SOFT_TRIGGERED, KillSwitchState.HARD_TRIGGERED},
    KillSwitchState.SOFT_TRIGGERED: {KillSwitchState.HARD_TRIGGERED, KillSwitchState.RECOVERY_PENDING},
    KillSwitchState.HARD_TRIGGERED: {KillSwitchState.RECOVERY_PENDING},
    KillSwitchState.RECOVERY_PENDING: {KillSwitchState.RECOVERY_APPROVED, KillSwitchState.HARD_TRIGGERED},
    KillSwitchState.RECOVERY_APPROVED: {KillSwitchState.ARMED},
}


def is_allowed_proposal_transition(current: ProposalState, target: ProposalState) -> bool:
    return target in _PROPOSAL_TRANSITIONS.get(current, set())


def is_allowed_kill_switch_transition(current: KillSwitchState, target: KillSwitchState) -> bool:
    return target in _KILL_SWITCH_TRANSITIONS.get(current, set())


__all__ = [
    "KillSwitchState",
    "ProposalState",
    "is_allowed_kill_switch_transition",
    "is_allowed_proposal_transition",
]


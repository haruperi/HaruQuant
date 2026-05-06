"""Governance services and state machines."""

from .workflow import (
    KillSwitchState,
    ProposalState,
    is_allowed_kill_switch_transition,
    is_allowed_proposal_transition,
)

__all__ = [
    "KillSwitchState",
    "ProposalState",
    "is_allowed_kill_switch_transition",
    "is_allowed_proposal_transition",
]


"""Workflow state-machine skeleton modules."""

from .proposal_transitions import (
    PROPOSAL_TRANSITIONS,
    is_allowed_proposal_transition,
)
from .states import (
    IncidentState,
    KillSwitchState,
    ProposalState,
    WorkflowState,
)
from .transitions import WORKFLOW_TRANSITIONS, is_allowed_workflow_transition

__all__ = [
    "IncidentState",
    "KillSwitchState",
    "PROPOSAL_TRANSITIONS",
    "ProposalState",
    "WORKFLOW_TRANSITIONS",
    "WorkflowState",
    "is_allowed_proposal_transition",
    "is_allowed_workflow_transition",
]

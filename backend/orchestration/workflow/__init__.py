"""Workflow state-machine skeleton modules."""

from .proposal_transitions import (
    PROPOSAL_TRANSITIONS,
    is_allowed_proposal_transition,
)
from .incident_transitions import (
    INCIDENT_TRANSITIONS,
    is_allowed_incident_transition,
)
from .states import (
    IncidentState,
    KillSwitchState,
    ProposalState,
    WorkflowState,
)
from .transitions import WORKFLOW_TRANSITIONS, is_allowed_workflow_transition

__all__ = [
    "INCIDENT_TRANSITIONS",
    "IncidentState",
    "KillSwitchState",
    "PROPOSAL_TRANSITIONS",
    "ProposalState",
    "WORKFLOW_TRANSITIONS",
    "WorkflowState",
    "is_allowed_incident_transition",
    "is_allowed_proposal_transition",
    "is_allowed_workflow_transition",
]

"""Workflow state-machine skeleton modules."""

from .kill_switch_transitions import (
    KILL_SWITCH_TRANSITIONS,
    is_allowed_kill_switch_transition,
)
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
from .services import WorkflowCreateRequest, WorkflowCreationService
from .persistence import WorkflowTransitionEvent, WorkflowTransitionLogger
from .validator import (
    WorkflowStateValidationError,
    WorkflowStateValidator,
    WorkflowValidationContext,
)

__all__ = [
    "INCIDENT_TRANSITIONS",
    "IncidentState",
    "KILL_SWITCH_TRANSITIONS",
    "KillSwitchState",
    "PROPOSAL_TRANSITIONS",
    "ProposalState",
    "WORKFLOW_TRANSITIONS",
    "WorkflowState",
    "WorkflowCreateRequest",
    "WorkflowCreationService",
    "WorkflowTransitionEvent",
    "WorkflowTransitionLogger",
    "is_allowed_incident_transition",
    "is_allowed_kill_switch_transition",
    "is_allowed_proposal_transition",
    "is_allowed_workflow_transition",
    "WorkflowStateValidationError",
    "WorkflowStateValidator",
    "WorkflowValidationContext",
]

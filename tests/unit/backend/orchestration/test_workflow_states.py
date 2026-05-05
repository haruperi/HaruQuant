from backend_retiring.orchestration.workflow import (
    IncidentState,
    KillSwitchState,
    ProposalState,
    WorkflowState,
)


def test_workflow_state_enum_matches_required_minimum_states() -> None:
    assert [state.value for state in WorkflowState] == [
        "CREATED",
        "REASONING",
        "PLANNING",
        "ACTING",
        "OBSERVING",
        "EVALUATING",
        "REFINING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "BLOCKED_BY_RISK",
        "BLOCKED_BY_POLICY",
        "TIMED_OUT",
        "RECONCILING",
    ]


def test_proposal_incident_and_kill_switch_state_enums_cover_required_values() -> None:
    assert [state.value for state in ProposalState] == [
        "DRAFT",
        "EVIDENCE_PENDING",
        "READY_FOR_RISK",
        "APPROVED",
        "APPROVED_WITH_LIMITS",
        "REJECTED",
        "EXPIRED",
        "EXECUTION_PENDING",
        "SENT",
        "ACKNOWLEDGED",
        "PARTIALLY_FILLED",
        "FILLED",
        "EXECUTION_FAILED",
        "CLOSED",
    ]
    assert [state.value for state in IncidentState] == [
        "DETECTED",
        "TRIAGED",
        "ACTIVE",
        "CONTAINED",
        "RESOLVED",
        "POSTMORTEM_PENDING",
        "CLOSED",
    ]
    assert [state.value for state in KillSwitchState] == [
        "ARMED",
        "SOFT_TRIGGERED",
        "HARD_TRIGGERED",
        "RECOVERY_PENDING",
        "RECOVERY_APPROVED",
    ]

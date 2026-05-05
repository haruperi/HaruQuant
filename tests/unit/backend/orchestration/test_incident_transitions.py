from backend_retiring.orchestration.workflow import (
    IncidentState,
    is_allowed_incident_transition,
)


def test_incident_transition_map_allows_expected_progression() -> None:
    assert is_allowed_incident_transition(IncidentState.DETECTED, IncidentState.TRIAGED)
    assert is_allowed_incident_transition(IncidentState.TRIAGED, IncidentState.ACTIVE)
    assert is_allowed_incident_transition(IncidentState.ACTIVE, IncidentState.CONTAINED)
    assert is_allowed_incident_transition(IncidentState.RESOLVED, IncidentState.POSTMORTEM_PENDING)
    assert is_allowed_incident_transition(IncidentState.POSTMORTEM_PENDING, IncidentState.CLOSED)


def test_incident_transition_map_rejects_invalid_and_terminal_paths() -> None:
    assert not is_allowed_incident_transition(IncidentState.DETECTED, IncidentState.RESOLVED)
    assert not is_allowed_incident_transition(IncidentState.ACTIVE, IncidentState.DETECTED)
    assert not is_allowed_incident_transition(IncidentState.CLOSED, IncidentState.ACTIVE)

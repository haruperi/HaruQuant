"""Incident transition rules."""

from __future__ import annotations

from .states import IncidentState


INCIDENT_TRANSITIONS: dict[IncidentState, frozenset[IncidentState]] = {
    IncidentState.DETECTED: frozenset(
        {
            IncidentState.TRIAGED,
            IncidentState.ACTIVE,
            IncidentState.CLOSED,
        }
    ),
    IncidentState.TRIAGED: frozenset(
        {
            IncidentState.ACTIVE,
            IncidentState.CONTAINED,
            IncidentState.RESOLVED,
            IncidentState.CLOSED,
        }
    ),
    IncidentState.ACTIVE: frozenset(
        {
            IncidentState.CONTAINED,
            IncidentState.RESOLVED,
            IncidentState.CLOSED,
        }
    ),
    IncidentState.CONTAINED: frozenset(
        {
            IncidentState.RESOLVED,
            IncidentState.POSTMORTEM_PENDING,
            IncidentState.CLOSED,
        }
    ),
    IncidentState.RESOLVED: frozenset(
        {
            IncidentState.POSTMORTEM_PENDING,
            IncidentState.CLOSED,
        }
    ),
    IncidentState.POSTMORTEM_PENDING: frozenset(
        {
            IncidentState.CLOSED,
        }
    ),
    IncidentState.CLOSED: frozenset(),
}


def is_allowed_incident_transition(
    from_state: IncidentState,
    to_state: IncidentState,
) -> bool:
    """Return whether an incident state transition is allowed."""

    return to_state in INCIDENT_TRANSITIONS[from_state]

from __future__ import annotations

from backend.contracts.common import Originator
from backend.contracts.observation_event.model import ObservationEvent, ObservationEventPayload
from haruquant.execution import classify_alert


def _observation(*, severity: str, observation_type: str, freshness_status: str = "fresh") -> ObservationEvent:
    return ObservationEvent(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="monitoring_agent"),
        environment="paper",
        operating_mode="MODE-002",
        payload=ObservationEventPayload(
            observation_id="obs_001",
            observation_type=observation_type,
            severity=severity,
            source="mt5_mcp",
            payload_ref_or_inline={"spread_pips": 2.1},
            authority_state={"state": "PROVISIONAL"},
            freshness_status=freshness_status,
            observed_at="2026-04-09T10:00:00Z",
        ),
    )


def test_classify_alert_maps_warning_and_stale_observations() -> None:
    warning = classify_alert(_observation(severity="warning", observation_type="spread_check"))
    stale = classify_alert(
        _observation(severity="info", observation_type="snapshot_check", freshness_status="stale")
    )

    assert warning.level == "warning"
    assert stale.level == "warning"


def test_classify_alert_maps_incident_and_kill_switch_paths() -> None:
    incident = classify_alert(_observation(severity="critical", observation_type="latency_spike"))
    kill_switch = classify_alert(
        _observation(severity="critical", observation_type="kill_switch_trigger")
    )

    assert incident.level == "incident"
    assert kill_switch.level == "kill_switch"

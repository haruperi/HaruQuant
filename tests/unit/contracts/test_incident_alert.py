from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.incident_alert.model import IncidentAlert, IncidentAlertPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "contracts"
    / "incident_alert"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_incident_alert_accepts_valid_example():
    contract = IncidentAlert.model_validate(_load_example("valid", "stale_market_warning.json"))

    assert contract.contract_type == "IncidentAlert"
    assert contract.payload.severity == "warning"
    assert contract.payload.incident_state == "open"


def test_incident_alert_rejects_invalid_incident_state():
    with pytest.raises(ValidationError):
        IncidentAlert.model_validate(_load_example("invalid", "bad_incident_state.json"))


def test_incident_alert_payload_requires_summary():
    with pytest.raises(ValidationError):
        IncidentAlertPayload(
            severity="warning",
            alert_type="stale_market_data",
            source="monitoring_service",
            recommended_action="Pause new entries until fresh market data is available.",
        )

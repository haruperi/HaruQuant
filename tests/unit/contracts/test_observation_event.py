from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend_retiring.contracts.observation_event.model import ObservationEvent, ObservationEventPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend_retiring"
    / "contracts"
    / "observation_event"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_observation_event_accepts_valid_example():
    contract = ObservationEvent.model_validate(_load_example("valid", "market_snapshot_notice.json"))

    assert contract.contract_type == "ObservationEvent"
    assert contract.payload.severity == "info"
    assert contract.payload.freshness_status == "fresh"


def test_observation_event_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        ObservationEvent.model_validate(_load_example("invalid", "bad_severity.json"))


def test_observation_event_payload_rejects_unknown_freshness_status():
    with pytest.raises(ValidationError):
        ObservationEventPayload(
            observation_id="obs_01",
            observation_type="market_snapshot",
            severity="info",
            source="market_data_mcp",
            payload_ref_or_inline={"snapshot_ref": "mktsnap_01"},
            authority_state={"authority": "broker_derived"},
            freshness_status="warm",
            observed_at="2026-04-08T10:20:59Z",
        )

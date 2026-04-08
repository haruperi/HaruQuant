from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.override_request.model import OverrideRequest, OverrideRequestPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "contracts"
    / "override_request"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_override_request_accepts_valid_example():
    contract = OverrideRequest.model_validate(_load_example("valid", "policy_exception.json"))

    assert contract.contract_type == "OverrideRequest"
    assert contract.payload.reason_code == "policy_exception"
    assert len(contract.payload.required_roles) == 2


def test_override_request_rejects_invalid_reason_code():
    with pytest.raises(ValidationError):
        OverrideRequest.model_validate(_load_example("invalid", "bad_reason_code.json"))


def test_override_request_payload_requires_roles():
    with pytest.raises(ValidationError):
        OverrideRequestPayload(
            override_request_id="ovrreq_01",
            original_decision_ref="risk_01",
            original_action_ref="prop_01",
            requested_action="permit reduced-size entry",
            reason_code="policy_exception",
            rationale="manual review completed",
            requested_expiry="2026-04-08T11:00:00Z",
            required_roles=[],
        )

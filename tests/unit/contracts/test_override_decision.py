from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.override_decision.model import OverrideDecision, OverrideDecisionPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3] / "contracts"
    / "override_decision"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_override_decision_accepts_valid_example():
    contract = OverrideDecision.model_validate(_load_example("valid", "approved_override.json"))

    assert contract.contract_type == "OverrideDecision"
    assert contract.payload.decision == "approved"
    assert len(contract.payload.approver_records) == 1


def test_override_decision_rejects_invalid_decision():
    with pytest.raises(ValidationError):
        OverrideDecision.model_validate(_load_example("invalid", "bad_decision.json"))


def test_override_decision_payload_requires_audit_ref():
    with pytest.raises(ValidationError):
        OverrideDecisionPayload(
            override_decision_id="ovrdec_01",
            override_request_id="ovrreq_01",
            decision="approved",
            approver_records=[
                {
                    "approver_id": "risk_manager_lead",
                    "role": "risk_manager",
                    "decision": "approved",
                    "decided_at": "2026-04-08T10:24:30Z",
                }
            ],
            effective_until="2026-04-08T11:00:00Z",
        )

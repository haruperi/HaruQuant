from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.risk_assessment_request.model import (
    RequestedFreshnessClasses,
    RiskAssessmentRequest,
)


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "contracts"
    / "risk_assessment_request"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_risk_assessment_request_accepts_valid_example():
    contract = RiskAssessmentRequest.model_validate(_load_example("valid", "new_entry_hot_snapshots.json"))

    assert contract.contract_type == "RiskAssessmentRequest"
    assert contract.payload.action_type == "new_entry"
    assert contract.payload.requested_freshness_classes.market_snapshot == "HOT"


def test_risk_assessment_request_rejects_invalid_freshness_class():
    with pytest.raises(ValidationError):
        RiskAssessmentRequest.model_validate(_load_example("invalid", "bad_freshness_class.json"))


def test_requested_freshness_classes_reject_unknown_value():
    with pytest.raises(ValidationError):
        RequestedFreshnessClasses(
            account_snapshot="HOT",
            portfolio_snapshot="STALE",
            market_snapshot="HOT",
        )

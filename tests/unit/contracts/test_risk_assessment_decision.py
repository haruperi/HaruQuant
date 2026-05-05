from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend_retiring.contracts.risk_assessment_decision.model import (
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend_retiring"
    / "contracts"
    / "risk_assessment_decision"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_risk_assessment_decision_accepts_valid_example():
    contract = RiskAssessmentDecision.model_validate(_load_example("valid", "approve_with_limits.json"))

    assert contract.contract_type == "RiskAssessmentDecision"
    assert contract.payload.decision == "APPROVE_WITH_LIMITS"
    assert len(contract.payload.limit_constraints) == 2


def test_risk_assessment_decision_rejects_invalid_decision():
    with pytest.raises(ValidationError):
        RiskAssessmentDecision.model_validate(_load_example("invalid", "bad_decision_value.json"))


def test_risk_assessment_decision_payload_requires_reason():
    with pytest.raises(ValidationError):
        RiskAssessmentDecisionPayload(
            risk_decision_id="risk_01",
            proposal_id="prop_01",
            decision="APPROVE",
            reasons=[],
            risk_metrics_snapshot={"var_95": 0.024},
            freshness_expiry="2026-04-08T10:16:40Z",
            policy_version="risk_policy_3.2.1",
            formula_version="risk_formula_1.4.0",
            provenance_bundle_ref={
                "bundle_id": "prov_01",
                "account_snapshot_ref": "acctsnap_101",
                "market_snapshot_ref": "mktsnap_455",
            },
        )

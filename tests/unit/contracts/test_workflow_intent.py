from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.workflow_intent.model import WorkflowIntent, WorkflowIntentPayload


EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "workflow_intent" / "examples"


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_workflow_intent_accepts_valid_example():
    contract = WorkflowIntent.model_validate(_load_example("valid", "trade_review.json"))

    assert contract.contract_type == "WorkflowIntent"
    assert contract.payload.workflow_type == "trade_review"
    assert contract.payload.trigger_type == "user_action"


def test_workflow_intent_rejects_missing_required_payload_field():
    with pytest.raises(ValidationError):
        WorkflowIntent.model_validate(_load_example("invalid", "missing_objective.json"))


def test_workflow_intent_payload_rejects_unknown_workflow_type():
    with pytest.raises(ValidationError):
        WorkflowIntentPayload(
            objective="Review EURUSD trade idea",
            workflow_type="manual_trade",
            trigger_type="user_action",
            requested_scope={"symbol_group": ["EURUSD"]},
        )

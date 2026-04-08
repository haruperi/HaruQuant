from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.execution_intent.model import ExecutionIntent, ExecutionIntentPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "contracts"
    / "execution_intent"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_execution_intent_accepts_valid_example():
    contract = ExecutionIntent.model_validate(_load_example("valid", "submit_limit_order.json"))

    assert contract.contract_type == "ExecutionIntent"
    assert contract.payload.broker_action_type == "submit_order"
    assert contract.payload.order_type == "limit"


def test_execution_intent_rejects_invalid_order_type():
    with pytest.raises(ValidationError):
        ExecutionIntent.model_validate(_load_example("invalid", "bad_order_type.json"))


def test_execution_intent_payload_rejects_unknown_side():
    with pytest.raises(ValidationError):
        ExecutionIntentPayload(
            execution_intent_id="exec_01",
            proposal_id="prop_01",
            risk_decision_id="risk_01",
            broker_action_type="submit_order",
            symbol="EURUSD",
            side="hold",
            size={"volume_lots": 0.25},
            order_type="limit",
            idempotency_key="idem_exec_01",
            expiry_time="2026-04-08T12:00:00Z",
            pre_send_validation_snapshot_ref="presend_01",
        )

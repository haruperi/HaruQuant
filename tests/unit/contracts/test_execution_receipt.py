from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.execution_receipt.model import ExecutionReceipt, ExecutionReceiptPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3] / "contracts"
    / "execution_receipt"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_execution_receipt_accepts_valid_example():
    contract = ExecutionReceipt.model_validate(_load_example("valid", "filled_limit_order.json"))

    assert contract.contract_type == "ExecutionReceipt"
    assert contract.payload.status == "filled"
    assert contract.payload.fill_qty == 0.25


def test_execution_receipt_rejects_invalid_status():
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(_load_example("invalid", "bad_status.json"))


def test_execution_receipt_payload_requires_receipt_hash():
    with pytest.raises(ValidationError):
        ExecutionReceiptPayload(
            receipt_id="rcpt_01",
            execution_intent_id="exec_01",
            broker="mt5",
            status="filled",
            authoritative_state={"position_state": "open"},
        )

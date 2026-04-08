from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.trade_hypothesis.model import TradeHypothesis, TradeHypothesisPayload


EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "backend" / "contracts" / "trade_hypothesis" / "examples"


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_trade_hypothesis_accepts_valid_example():
    contract = TradeHypothesis.model_validate(_load_example("valid", "eurusd_buy.json"))

    assert contract.contract_type == "TradeHypothesis"
    assert contract.payload.direction == "buy"
    assert contract.payload.confidence == 0.74


def test_trade_hypothesis_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        TradeHypothesis.model_validate(_load_example("invalid", "confidence_out_of_range.json"))


def test_trade_hypothesis_payload_rejects_unknown_direction():
    with pytest.raises(ValidationError):
        TradeHypothesisPayload(
            hypothesis_id="hyp_01",
            symbol="EURUSD",
            direction="hold",
            thesis="test",
            entry_rationale="test",
            invalidation_rationale="test",
            stop_loss_logic={"type": "fixed"},
            holding_horizon="intraday",
            confidence=0.5,
            calibration_note="test",
            evidence=[{"source_type": "market", "ref_id": "snap_01", "summary": "ok"}],
            required_validation_data=["market_snapshot"],
            strategy_family="trend_following",
            feature_version="feat_v3",
            strategy_code_hash="sha256:abc123",
        )

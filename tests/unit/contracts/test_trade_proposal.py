from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.trade_proposal.model import TradeProposal, TradeProposalPayload


EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "trade_proposal" / "examples"


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_trade_proposal_accepts_valid_example():
    contract = TradeProposal.model_validate(_load_example("valid", "eurusd_ready_for_risk.json"))

    assert contract.contract_type == "TradeProposal"
    assert contract.payload.readiness_state == "ready_for_risk"
    assert contract.payload.direction == "buy"


def test_trade_proposal_rejects_invalid_readiness_state():
    with pytest.raises(ValidationError):
        TradeProposal.model_validate(_load_example("invalid", "bad_readiness_state.json"))


def test_trade_proposal_payload_rejects_unknown_direction():
    with pytest.raises(ValidationError):
        TradeProposalPayload(
            proposal_id="prop_01",
            source_hypothesis_id="hyp_01",
            symbol="EURUSD",
            direction="hold",
            candidate_price_logic={"type": "limit_retest"},
            proposed_size={"volume_lots": 0.25},
            operating_envelope={"max_spread_pips": 1.5},
            expiry_at="2026-04-08T12:00:00Z",
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        )

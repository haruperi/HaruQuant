from __future__ import annotations

from datetime import datetime, timezone

from haruquant.utils import FixedClock
from backend_retiring.contracts.trade_proposal.model import TradeProposal
from haruquant.risk import (
    enforce_risk_decision_expiry,
    invalidate_for_material_proposal_change,
)


UTC = timezone.utc


def _proposal(*, size_units: int) -> TradeProposal:
    return TradeProposal.model_validate(
        {
            "workflow_id": "wf_001",
            "correlation_id": "corr_001",
            "causation_id": "evt_001",
            "timestamp_utc": "2026-04-09T10:00:00Z",
            "originator": {"type": "service", "id": "proposal-service"},
            "environment": "dev",
            "operating_mode": "MODE-002",
            "contract_type": "TradeProposal",
            "payload": {
                "proposal_id": "prop_001",
                "source_hypothesis_id": "hyp_001",
                "symbol": "EURUSD",
                "direction": "buy",
                "candidate_price_logic": {"entry": "market"},
                "proposed_size": {"units": size_units},
                "operating_envelope": {"strategy_id": "strat_001"},
                "session_restrictions": {"session": "london"},
                "expiry_at": "2026-04-09T10:05:00Z",
                "transformation_version": "proposal_v1",
                "readiness_state": "ready_for_risk",
            },
        }
    )


def test_invalidate_for_material_proposal_change_flags_changed_size():
    result = invalidate_for_material_proposal_change(
        approved_proposal=_proposal(size_units=1000),
        current_proposal=_proposal(size_units=1200),
    )

    assert result.valid is False
    assert result.reason_codes == ("material_proposal_change",)


def test_enforce_risk_decision_expiry_rejects_expired_decision():
    result = enforce_risk_decision_expiry(
        freshness_expiry=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 31, tzinfo=UTC)),
    )

    assert result.valid is False
    assert result.reason_codes == ("risk_decision_expired",)

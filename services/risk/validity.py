"""Risk-decision validity helpers for change and expiry enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.utils.logger import logger
from services.utils import Clock, SystemClock
from backend.contracts.trade_proposal.model import TradeProposal


@dataclass(frozen=True)
class RiskDecisionValidity:
    """Validity result for an already-issued risk decision."""

    valid: bool
    reason_codes: tuple[str, ...] = ()


def _proposal_material_fingerprint(proposal: TradeProposal) -> tuple[object, ...]:
    payload = proposal.payload
    return (
        payload.symbol,
        payload.direction,
        tuple(sorted(payload.candidate_price_logic.items())),
        tuple(sorted(payload.proposed_size.items())),
        tuple(sorted(payload.operating_envelope.items())),
        tuple(sorted(payload.session_restrictions.items())),
        payload.expiry_at,
        payload.transformation_version,
    )


def invalidate_for_material_proposal_change(
    *,
    approved_proposal: TradeProposal,
    current_proposal: TradeProposal,
) -> RiskDecisionValidity:
    """Invalidate prior risk approval when material proposal fields change."""

    if _proposal_material_fingerprint(approved_proposal) == _proposal_material_fingerprint(
        current_proposal
    ):
        return RiskDecisionValidity(valid=True)
    return RiskDecisionValidity(valid=False, reason_codes=("material_proposal_change",))


def enforce_risk_decision_expiry(
    *,
    freshness_expiry: datetime,
    clock: Clock | None = None,
) -> RiskDecisionValidity:
    """Invalidate risk approval when its expiry timestamp has passed."""

    active_clock = clock or SystemClock()
    if freshness_expiry >= active_clock.now():
        return RiskDecisionValidity(valid=True)
    return RiskDecisionValidity(valid=False, reason_codes=("risk_decision_expired",))
__all__ = [
    "RiskDecisionValidity",
    "enforce_risk_decision_expiry",
    "invalidate_for_material_proposal_change",
]

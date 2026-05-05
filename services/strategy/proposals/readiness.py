"""Proposal readiness evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from contracts.trade_hypothesis.model import TradeHypothesis
from contracts.trade_proposal.model import TradeProposal


@dataclass(frozen=True)
class ProposalReadinessResult:
    """Simple readiness verdict for a proposal before risk review."""

    ready: bool
    readiness_state: str
    reason_codes: tuple[str, ...] = ()


def evaluate_proposal_readiness(
    proposal: TradeProposal,
    *,
    source_hypothesis: TradeHypothesis | None = None,
) -> ProposalReadinessResult:
    """Fail closed when proposal inputs are incomplete for risk review."""

    reasons: list[str] = []
    payload = proposal.payload

    if not payload.candidate_price_logic:
        reasons.append("missing_candidate_price_logic")
    if not payload.proposed_size:
        reasons.append("missing_proposed_size")
    if not payload.operating_envelope:
        reasons.append("missing_operating_envelope")

    if source_hypothesis is not None:
        if source_hypothesis.payload.required_validation_data:
            reasons.append("missing_required_validation_data")
        if payload.source_hypothesis_id != source_hypothesis.payload.hypothesis_id:
            reasons.append("source_hypothesis_mismatch")

    if reasons:
        return ProposalReadinessResult(
            ready=False,
            readiness_state="rejected",
            reason_codes=tuple(reasons),
        )

    return ProposalReadinessResult(
        ready=True,
        readiness_state="ready_for_risk",
    )

"""Trade hypothesis to proposal transformation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from apps.core import Clock, SystemClock
from apps.core.ids import generate_id
from backend.contracts.trade_hypothesis.model import TradeHypothesis
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload


@dataclass(frozen=True)
class ProposalTransformationConfig:
    """Minimal configuration for hypothesis-to-proposal transformation."""

    transformation_version: str = "proposal_transformer_v1"
    expiry_ttl: timedelta = timedelta(minutes=30)
    default_operating_envelope: dict[str, object] | None = None
    default_session_restrictions: dict[str, object] | None = None


def transform_hypothesis_to_proposal(
    hypothesis: TradeHypothesis,
    *,
    clock: Clock | None = None,
    config: ProposalTransformationConfig | None = None,
) -> TradeProposal:
    """Create a draft proposal from a non-executable trade hypothesis."""

    active_clock = clock or SystemClock()
    active_config = config or ProposalTransformationConfig()
    payload = hypothesis.payload
    current_time = active_clock.now()

    return TradeProposal(
        workflow_id=hypothesis.workflow_id,
        correlation_id=hypothesis.correlation_id,
        causation_id=hypothesis.causation_id,
        timestamp_utc=current_time,
        originator=hypothesis.originator,
        environment=hypothesis.environment,
        operating_mode=hypothesis.operating_mode,
        tenant_id=hypothesis.tenant_id,
        account_scope_id=hypothesis.account_scope_id,
        strategy_scope_id=hypothesis.strategy_scope_id,
        compliance_profile_id=hypothesis.compliance_profile_id,
        trace_id=hypothesis.trace_id,
        replay_bundle_hint=hypothesis.replay_bundle_hint,
        payload=TradeProposalPayload(
            proposal_id=generate_id("proposal"),
            source_hypothesis_id=payload.hypothesis_id,
            symbol=payload.symbol,
            direction=payload.direction,
            candidate_price_logic={
                "entry_rationale": payload.entry_rationale,
                "stop_loss_logic": payload.stop_loss_logic,
                "take_profit_logic": payload.take_profit_logic,
            },
            proposed_size={"sizing_state": "pending_risk_sizing"},
            operating_envelope=active_config.default_operating_envelope or {},
            session_restrictions=active_config.default_session_restrictions or {},
            expiry_at=current_time + active_config.expiry_ttl,
            transformation_version=active_config.transformation_version,
            readiness_state="draft",
        ),
    )

"""Execution intent assembly from approved proposal and risk decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from services.utils import Clock, SystemClock
from services.utils.ids import generate_id
from services.utils.logger import logger
from backend.contracts.execution_intent.model import ExecutionIntent, ExecutionIntentPayload
from backend.contracts.risk_assessment_decision.model import RiskAssessmentDecision
from backend.contracts.trade_proposal.model import TradeProposal


@dataclass(frozen=True)
class ExecutionIntentAssemblyConfig:
    """Static defaults for execution intent assembly."""

    broker_action_type: str = "submit_order"
    order_type: str = "market"
    expiry_ttl: timedelta = timedelta(minutes=5)
    validation_snapshot_ref: str = "pre_send_validation_pending"


def assemble_execution_intent(
    proposal: TradeProposal,
    risk_decision: RiskAssessmentDecision,
    *,
    idempotency_key: str,
    clock: Clock | None = None,
    config: ExecutionIntentAssemblyConfig | None = None,
) -> ExecutionIntent:
    """Build a canonical execution intent linked to the approved proposal and risk decision."""

    if risk_decision.payload.proposal_id != proposal.payload.proposal_id:
        raise ValueError("risk decision does not match proposal")
    if risk_decision.payload.decision not in {"APPROVE", "APPROVE_WITH_LIMITS"}:
        raise ValueError("risk decision is not execution-eligible")

    active_clock = clock or SystemClock()
    active_config = config or ExecutionIntentAssemblyConfig()
    current_time = active_clock.now()

    return ExecutionIntent(
        workflow_id=proposal.workflow_id,
        correlation_id=proposal.correlation_id,
        causation_id=risk_decision.causation_id,
        timestamp_utc=current_time,
        originator=risk_decision.originator,
        environment=proposal.environment,
        operating_mode=proposal.operating_mode,
        tenant_id=proposal.tenant_id,
        account_scope_id=proposal.account_scope_id,
        strategy_scope_id=proposal.strategy_scope_id,
        compliance_profile_id=proposal.compliance_profile_id,
        trace_id=proposal.trace_id,
        replay_bundle_hint=proposal.replay_bundle_hint,
        payload=ExecutionIntentPayload(
            execution_intent_id=generate_id("execution_intent"),
            proposal_id=proposal.payload.proposal_id,
            risk_decision_id=risk_decision.payload.risk_decision_id,
            broker_action_type=active_config.broker_action_type,
            symbol=proposal.payload.symbol,
            side=proposal.payload.direction,
            size=proposal.payload.proposed_size,
            order_type=active_config.order_type,
            price_params=proposal.payload.candidate_price_logic,
            sl_tp_params={
                key: value
                for key, value in proposal.payload.candidate_price_logic.items()
                if key in {"stop_loss_logic", "take_profit_logic"}
            },
            idempotency_key=idempotency_key,
            expiry_time=current_time + active_config.expiry_ttl,
            pre_send_validation_snapshot_ref=active_config.validation_snapshot_ref,
        ),
    )

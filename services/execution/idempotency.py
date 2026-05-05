"""Execution idempotency helpers."""

from __future__ import annotations

import hashlib

from backend_retiring.contracts.execution_intent.model import ExecutionIntent
from backend_retiring.contracts.serialization import canonical_json_dumps
from backend_retiring.contracts.risk_assessment_decision.model import RiskAssessmentDecision
from backend_retiring.contracts.trade_proposal.model import TradeProposal

from services.utils.logger import logger

def generate_execution_idempotency_key(
    *,
    proposal: TradeProposal,
    risk_decision: RiskAssessmentDecision,
    broker_action_type: str,
    order_type: str,
) -> str:
    """Generate a stable uniqueness key for one execution request shape."""

    fingerprint = canonical_json_dumps(
        {
            "workflow_id": proposal.workflow_id,
            "proposal_id": proposal.payload.proposal_id,
            "risk_decision_id": risk_decision.payload.risk_decision_id,
            "symbol": proposal.payload.symbol,
            "direction": proposal.payload.direction,
            "proposed_size": proposal.payload.proposed_size,
            "candidate_price_logic": proposal.payload.candidate_price_logic,
            "broker_action_type": broker_action_type,
            "order_type": order_type,
        }
    )
    return f"idem_{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()}"

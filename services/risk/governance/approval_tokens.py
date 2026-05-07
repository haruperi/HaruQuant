"""Approval-token generation and validation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from services.risk.domain.contracts import RiskApprovalToken, RiskProposal
from services.risk.domain.exceptions import RiskTokenError
from services.risk.governance.signatures import sign_payload, stable_hash

USED_APPROVAL_SIGNATURES: set[str] = set()


def create_approval_token(
    *,
    decision_id: str,
    proposal: RiskProposal,
    approved_volume: float,
    risk_metrics_snapshot: dict[str, Any],
    portfolio_snapshot: dict[str, Any],
    market_snapshot: dict[str, Any],
    config_hash: str,
    policy_version: str,
    ttl_seconds: int,
    audit_ref: str,
) -> RiskApprovalToken:
    valid_from = datetime.now(timezone.utc)
    expires_at = valid_from + timedelta(seconds=ttl_seconds)
    unsigned = {
        "decision_id": decision_id,
        "proposal_id": proposal.proposal_id,
        "strategy_id": proposal.strategy_id,
        "symbol": proposal.symbol,
        "side": proposal.side,
        "order_type": proposal.order_type,
        "approved_volume": approved_volume,
        "expires_at": expires_at.isoformat(),
        "config_hash": config_hash,
    }
    signature = sign_payload(unsigned, namespace="risk_approval_token")
    return RiskApprovalToken(
        approval_id=f"risk-{signature[:16]}",
        decision_id=decision_id,
        proposal_id=proposal.proposal_id,
        strategy_id=proposal.strategy_id,
        strategy_code_hash=proposal.strategy_code_hash,
        symbol=proposal.symbol,
        side=proposal.side,
        order_type=proposal.order_type,
        requested_volume=proposal.requested_volume,
        approved_volume=approved_volume,
        max_price_deviation=0.0005,
        account_id="default-account",
        broker_id="configured-broker",
        valid_from=valid_from.isoformat(),
        expires_at=expires_at.isoformat(),
        single_use=True,
        used_at=None,
        risk_metrics_snapshot=risk_metrics_snapshot,
        portfolio_state_hash=stable_hash(portfolio_snapshot),
        market_state_hash=stable_hash(market_snapshot),
        config_version_hash=config_hash,
        policy_version=policy_version,
        signature=signature,
        audit_ref=audit_ref,
    )


def validate_approval_token(token: dict[str, Any] | RiskApprovalToken, *, proposal: dict[str, Any] | None = None, mark_used: bool = True) -> bool:
    payload = asdict(token) if isinstance(token, RiskApprovalToken) else dict(token)
    if datetime.fromisoformat(payload["expires_at"]) < datetime.now(timezone.utc):
        raise RiskTokenError("approval_token_expired")
    if payload.get("single_use", True) and payload["signature"] in USED_APPROVAL_SIGNATURES:
        raise RiskTokenError("approval_token_replayed")
    if proposal:
        if str(proposal.get("proposal_id")) != payload["proposal_id"]:
            raise RiskTokenError("proposal_id_changed")
        if float(proposal.get("requested_volume", proposal.get("requested_size", 0.0))) > float(payload["approved_volume"]):
            raise RiskTokenError("requested_volume_exceeds_approval")
        for field in ("symbol", "side", "order_type"):
            if field in proposal and str(proposal[field]) != str(payload[field]):
                raise RiskTokenError(f"{field}_changed")
    if mark_used:
        USED_APPROVAL_SIGNATURES.add(payload["signature"])
    return True

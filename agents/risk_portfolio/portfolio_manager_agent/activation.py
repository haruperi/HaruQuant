"""Live activation workflow contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import Field

from agents._shared.persistence import utc_stamp, write_json_artifact
from agents._shared.schemas import FirmModel


class LiveActivationRequest(FirmModel):
    strategy_id: str
    strategy_version: str
    backtest_evidence: list[str] = Field(default_factory=list)
    robustness_evidence: list[str] = Field(default_factory=list)
    paper_trading_evidence: list[str] = Field(default_factory=list)
    risk_memo: str
    portfolio_memo: str
    requested_allocation: float = Field(ge=0.0, le=1.0)
    max_risk_per_trade: float = Field(gt=0.0, le=0.05)
    kill_switch_status: str
    broker_readiness_status: str


@dataclass(frozen=True)
class BoardApprovalDecision:
    approval_id: str
    status: str
    approval_scope: str
    expires_at: str
    evidence_pack: dict[str, Any]
    audit_uri: str
    reasons: list[str] = field(default_factory=list)


class LiveActivationWorkflow:
    """Requires evidence, risk, portfolio, kill-switch, broker, and Board approval."""

    def build_board_pack(self, request: LiveActivationRequest) -> dict[str, Any]:
        return {
            "strategy_id": request.strategy_id,
            "strategy_version": request.strategy_version,
            "full_evidence_pack": {
                "backtest_evidence": request.backtest_evidence,
                "robustness_evidence": request.robustness_evidence,
                "paper_trading_evidence": request.paper_trading_evidence,
                "risk_memo": request.risk_memo,
                "portfolio_memo": request.portfolio_memo,
            },
            "risk_limits": {
                "requested_allocation": request.requested_allocation,
                "max_risk_per_trade": request.max_risk_per_trade,
            },
            "expected_worst_case_behavior": "Kill switch disables new orders and escalation requires Human Board review.",
            "promotion_reason": "Evidence pack passed deterministic activation prerequisites.",
            "approval_options": ["reject", "approve_micro_live", "approve_limited_live"],
            "approval_expiration": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }

    def validate_prerequisites(self, request: LiveActivationRequest) -> list[str]:
        failures: list[str] = []
        if not request.backtest_evidence:
            failures.append("missing_backtest_evidence")
        if not request.robustness_evidence:
            failures.append("missing_robustness_evidence")
        if not request.paper_trading_evidence:
            failures.append("missing_paper_trading_evidence")
        if request.kill_switch_status != "healthy":
            failures.append("kill_switch_not_healthy")
        if request.broker_readiness_status != "ready":
            failures.append("broker_not_ready")
        if request.requested_allocation <= 0:
            failures.append("invalid_allocation")
        return failures

    def request_board_approval(self, request: LiveActivationRequest, *, approval_scope: str = "micro_live") -> BoardApprovalDecision:
        pack = self.build_board_pack(request)
        failures = self.validate_prerequisites(request)
        status = "pending_board" if not failures else "blocked"
        approval_id = hashlib.sha256(json.dumps(pack, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        audit_uri = write_json_artifact("reports/board", f"live-activation-{approval_id}-{utc_stamp()}.json", pack)
        return BoardApprovalDecision(
            approval_id=f"board-{approval_id}",
            status=status,
            approval_scope=approval_scope,
            expires_at=pack["approval_expiration"],
            evidence_pack=pack,
            audit_uri=audit_uri,
            reasons=failures,
        )


__all__ = ["BoardApprovalDecision", "LiveActivationRequest", "LiveActivationWorkflow"]

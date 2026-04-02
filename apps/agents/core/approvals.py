"""File-backed approval artifacts for privileged agent actions."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from apps.agents.core.agent_models import ApprovalDecision, ApprovalRequest
from apps.agents.core.audit import AgentAuditEvent, AgentAuditLogger


class ApprovalStatus:
    """Simple enum-like helper for approval artifact states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all supported approval states."""
        return (cls.PENDING, cls.APPROVED, cls.REJECTED, cls.APPLIED)


class ApprovalDecisionType:
    """Simple enum-like helper for human approval decisions."""

    APPROVE = "approve"
    REJECT = "reject"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all supported approval decisions."""
        return (cls.APPROVE, cls.REJECT)


class ApprovalActionType:
    """Known privileged action families supported by the agent layer."""

    STRATEGY_PROMOTION = "strategy_promotion"
    LIVE_DEPLOYMENT = "live_deployment"
    LIVE_PAUSE_SESSION = "live_pause_session"
    LIVE_STOP_SESSION = "live_stop_session"
    RISK_OVERRIDE = "risk_override"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all supported approval action types."""
        return (
            cls.STRATEGY_PROMOTION,
            cls.LIVE_DEPLOYMENT,
            cls.LIVE_PAUSE_SESSION,
            cls.LIVE_STOP_SESSION,
            cls.RISK_OVERRIDE,
        )


def build_target_ref(action_type: str, payload: Dict[str, Any]) -> str:
    """Build the canonical target reference for one privileged action."""
    normalized = str(action_type).strip().lower()
    if normalized == ApprovalActionType.STRATEGY_PROMOTION:
        return f"strategy_version:{int(payload['strategy_version_id'])}"
    if normalized in (ApprovalActionType.LIVE_PAUSE_SESSION, ApprovalActionType.LIVE_STOP_SESSION):
        return f"live_session:{int(payload['session_id'])}"
    if normalized == ApprovalActionType.LIVE_DEPLOYMENT:
        return f"live_deployment:{int(payload['session_id'])}"
    if normalized == ApprovalActionType.RISK_OVERRIDE:
        return f"risk_override:{str(payload['key']).strip()}"
    raise ValueError(f"Unsupported approval action type: {action_type}")


class ApprovalStore:
    """Persist approval artifacts as one JSON file per request."""

    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)

    def create_request(
        self,
        *,
        action_type: str,
        requested_by_user_id: int,
        requested_by_role: str,
        rationale: str,
        request_payload: Dict[str, Any],
    ) -> ApprovalRequest:
        """Create and persist one pending approval request."""
        normalized_action = str(action_type).strip().lower()
        if normalized_action not in ApprovalActionType.values():
            raise ValueError(f"Unsupported approval action type: {action_type}")
        approval = ApprovalRequest(
            approval_id=f"apr-{uuid4().hex[:16]}",
            action_type=normalized_action,
            target_ref=build_target_ref(normalized_action, request_payload),
            requested_by_user_id=int(requested_by_user_id),
            requested_by_role=str(requested_by_role).strip(),
            rationale=str(rationale).strip(),
            request_payload=dict(request_payload),
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write(approval)
        return approval

    def get_request(self, approval_id: str) -> ApprovalRequest:
        """Load one approval artifact from disk."""
        approval_path = self.store_dir / f"{approval_id}.json"
        if not approval_path.exists():
            raise FileNotFoundError(f"Approval request not found: {approval_id}")
        raw = json.loads(approval_path.read_text(encoding="utf-8"))
        return ApprovalRequest(**raw)

    def apply_decision(self, decision: ApprovalDecision) -> ApprovalRequest:
        """Apply one approve/reject decision to a pending approval request."""
        approval = self.get_request(decision.approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval request is not pending: {decision.approval_id}")
        normalized_decision = str(decision.decision).strip().lower()
        if normalized_decision not in ApprovalDecisionType.values():
            raise ValueError(f"Unsupported approval decision: {decision.decision}")
        updated = replace(
            approval,
            status=(
                ApprovalStatus.APPROVED
                if normalized_decision == ApprovalDecisionType.APPROVE
                else ApprovalStatus.REJECTED
            ),
            decision=normalized_decision,
            decision_notes=str(decision.notes).strip(),
            decided_by_user_id=int(decision.actor_user_id),
            decided_by_role=str(decision.actor_role).strip(),
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write(updated)
        return updated

    def mark_applied(
        self,
        *,
        approval_id: str,
        execution_metadata: Dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """Mark one approved request as applied."""
        approval = self.get_request(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Approval request is not approved: {approval_id}")
        updated = replace(
            approval,
            status=ApprovalStatus.APPLIED,
            executed_at=datetime.now(timezone.utc).isoformat(),
            execution_metadata=dict(execution_metadata or {}),
        )
        self._write(updated)
        return updated

    def require_approved_request(
        self,
        *,
        approval_id: str,
        action_type: str,
        target_ref: str,
    ) -> ApprovalRequest:
        """Validate that one approval artifact matches the intended action."""
        approval = self.get_request(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Approval request is not approved: {approval_id}")
        if approval.action_type != str(action_type).strip().lower():
            raise ValueError("Approval action type does not match requested privileged action.")
        if approval.target_ref != str(target_ref).strip():
            raise ValueError("Approval target does not match requested privileged action.")
        return approval

    def _write(self, approval: ApprovalRequest) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        approval_path = self.store_dir / f"{approval.approval_id}.json"
        approval_path.write_text(json.dumps(approval.to_dict(), sort_keys=True, indent=2), encoding="utf-8")


def append_approval_audit_event(
    audit_logger: AgentAuditLogger,
    *,
    approval: ApprovalRequest,
    event_type: str,
    actor_user_id: int,
    actor_role: str,
    status: str,
    metadata: Dict[str, Any] | None = None,
) -> None:
    """Append one approval-focused audit event."""
    audit_logger.append(
        AgentAuditEvent(
            event_type=event_type,
            task_id=approval.approval_id,
            run_id=approval.request_payload.get("run_id", ""),
            workflow_name=approval.action_type,
            correlation_id=str(approval.request_payload.get("correlation_id") or ""),
            status=status,
            user_id=int(actor_user_id),
            actor_role=actor_role,
            metadata=dict(metadata or {}),
            approval_event=approval.to_dict(),
        )
    )

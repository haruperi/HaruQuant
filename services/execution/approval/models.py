"""Approval domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, List, Optional


class ApprovalState(StrEnum):
    PENDING = "PENDING"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RiskClass(StrEnum):
    """Action risk classification (Playbook §11.1)."""
    A = "A"  # read-only, no side effect
    B = "B"  # low-risk write, reversible
    C = "C"  # material write, approval-worthy
    D = "D"  # high-risk, financially material, compliance sensitive
    E = "E"  # irreversible or prohibited


@dataclass(frozen=True)
class ApprovalPacket:
    """Full approval packet (Playbook §11.2, §11.3)."""
    action: str
    reason: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: Dict[str, str] = field(default_factory=dict)
    policy_checks_passed: List[str] = field(default_factory=list)
    risk_class: RiskClass = RiskClass.C
    alternatives_considered: List[str] = field(default_factory=list)
    expected_impact: Dict[str, Any] = field(default_factory=dict)
    rollback_plan: str = ""
    escalation_triggers: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Return True if all required fields are populated."""
        return bool(
            self.action
            and self.reason
            and self.risk_class
            and self.rollback_plan
        )

    def missing_fields(self) -> List[str]:
        """Return list of required fields that are empty."""
        missing = []
        if not self.action:
            missing.append("action")
        if not self.reason:
            missing.append("reason")
        if not self.risk_class:
            missing.append("risk_class")
        if not self.rollback_plan:
            missing.append("rollback_plan")
        return missing


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    action_type: str
    target_ref_type: str
    target_ref_id: str
    required_count: int
    state: ApprovalState
    created_by_actor_type: str
    created_by_actor_id: str
    compliance_profile_id: str | None = None
    expires_at: str | None = None
    packet: ApprovalPacket | None = None

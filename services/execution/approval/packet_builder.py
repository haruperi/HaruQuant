"""Approval packet builder helper."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.execution.approval.models import ApprovalPacket, RiskClass


class ApprovalPacketBuilder:
    """Fluent builder for ApprovalPacket."""

    def __init__(self) -> None:
        self._action = ""
        self._reason = ""
        self._evidence: List[Dict[str, Any]] = []
        self._confidence = 0.0
        self._uncertainty: Dict[str, str] = {}
        self._policy_checks: List[str] = []
        self._risk_class = RiskClass.C
        self._alternatives: List[str] = []
        self._impact: Dict[str, Any] = {}
        self._rollback = ""
        self._escalation: List[str] = []

    def action(self, value: str) -> "ApprovalPacketBuilder":
        self._action = value
        return self

    def reason(self, value: str) -> "ApprovalPacketBuilder":
        self._reason = value
        return self

    def evidence(self, items: List[Dict[str, Any]]) -> "ApprovalPacketBuilder":
        self._evidence = list(items)
        return self

    def confidence(self, value: float) -> "ApprovalPacketBuilder":
        self._confidence = value
        return self

    def uncertainty(self, items: Dict[str, str]) -> "ApprovalPacketBuilder":
        self._uncertainty = dict(items)
        return self

    def policy_checks(self, items: List[str]) -> "ApprovalPacketBuilder":
        self._policy_checks = list(items)
        return self

    def risk_class(self, value: RiskClass) -> "ApprovalPacketBuilder":
        self._risk_class = value
        return self

    def alternatives(self, items: List[str]) -> "ApprovalPacketBuilder":
        self._alternatives = list(items)
        return self

    def expected_impact(self, value: Dict[str, Any]) -> "ApprovalPacketBuilder":
        self._impact = dict(value)
        return self

    def rollback_plan(self, value: str) -> "ApprovalPacketBuilder":
        self._rollback = value
        return self

    def escalation_triggers(self, items: List[str]) -> "ApprovalPacketBuilder":
        self._escalation = list(items)
        return self

    def build(self) -> ApprovalPacket:
        return ApprovalPacket(
            action=self._action,
            reason=self._reason,
            evidence=self._evidence,
            confidence=self._confidence,
            uncertainty=self._uncertainty,
            policy_checks_passed=self._policy_checks,
            risk_class=self._risk_class,
            alternatives_considered=self._alternatives,
            expected_impact=self._impact,
            rollback_plan=self._rollback,
            escalation_triggers=self._escalation,
        )

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ApprovalPacketBuilder":
        """Create builder from dictionary."""
        b = ApprovalPacketBuilder()
        b.action(data.get("action", ""))
        b.reason(data.get("reason", ""))
        b.evidence(data.get("evidence", []))
        b.confidence(float(data.get("confidence", 0.0)))
        b.uncertainty(data.get("uncertainty", {}))
        b.policy_checks(data.get("policy_checks_passed", []))
        risk = data.get("risk_class", "C")
        b.risk_class(RiskClass(risk))
        b.alternatives(data.get("alternatives_considered", []))
        b.expected_impact(data.get("expected_impact", {}))
        b.rollback_plan(data.get("rollback_plan", ""))
        b.escalation_triggers(data.get("escalation_triggers", []))
        return b

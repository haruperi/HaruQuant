"""Tests for approval packet and packet builder."""

from __future__ import annotations

import pytest

from backend.services.approval import (
    ApprovalPacket,
    ApprovalPacketBuilder,
    ApprovalRequest,
    ApprovalState,
    RiskClass,
)


class TestRiskClass:
    def test_all_risk_classes_exist(self) -> None:
        assert RiskClass.A == "A"
        assert RiskClass.B == "B"
        assert RiskClass.C == "C"
        assert RiskClass.D == "D"
        assert RiskClass.E == "E"


class TestApprovalPacket:
    def test_defaults(self) -> None:
        pkt = ApprovalPacket(action="test", reason="because")
        assert pkt.action == "test"
        assert pkt.reason == "because"
        assert pkt.evidence == []
        assert pkt.confidence == 0.0
        assert pkt.uncertainty == {}
        assert pkt.policy_checks_passed == []
        assert pkt.risk_class == RiskClass.C
        assert pkt.alternatives_considered == []
        assert pkt.expected_impact == {}
        assert pkt.rollback_plan == ""
        assert pkt.escalation_triggers == []

    def test_is_complete_with_required_fields(self) -> None:
        pkt = ApprovalPacket(
            action="place_order",
            reason="Signal confirmed",
            rollback_plan="close_position",
            risk_class=RiskClass.D,
        )
        assert pkt.is_complete() is True

    def test_is_complete_missing_action(self) -> None:
        pkt = ApprovalPacket(
            action="",
            reason="because",
            rollback_plan="undo",
        )
        assert pkt.is_complete() is False

    def test_is_complete_missing_rollback(self) -> None:
        pkt = ApprovalPacket(
            action="test",
            reason="because",
            rollback_plan="",
        )
        assert pkt.is_complete() is False

    def test_missing_fields(self) -> None:
        pkt = ApprovalPacket(action="", reason="", rollback_plan="")
        missing = pkt.missing_fields()
        assert "action" in missing
        assert "reason" in missing
        assert "rollback_plan" in missing

    def test_missing_fields_none_missing(self) -> None:
        pkt = ApprovalPacket(
            action="x", reason="y", rollback_plan="z",
        )
        assert pkt.missing_fields() == []

    def test_full_packet(self) -> None:
        pkt = ApprovalPacket(
            action="place_order",
            reason="Signal confirmed by strategy and risk checks",
            evidence=[
                {"source": "signal_summary", "value": "bullish"},
                {"source": "risk_policy_check", "value": "pass"},
            ],
            confidence=0.86,
            uncertainty={"market_regime": "unknown"},
            policy_checks_passed=["var_check", "margin_check"],
            risk_class=RiskClass.D,
            alternatives_considered=["reduce_size", "defer_trade"],
            expected_impact={"financial": "+500", "risk": "low"},
            rollback_plan="close_position_if_post_check_fails",
            escalation_triggers=[
                "policy_conflict",
                "missing_evidence",
            ],
        )
        assert pkt.is_complete()
        assert len(pkt.evidence) == 2
        assert pkt.confidence == 0.86
        assert len(pkt.escalation_triggers) == 2


class TestApprovalRequestWithPacket:
    def test_request_with_packet(self) -> None:
        pkt = ApprovalPacket(
            action="test", reason="test", rollback_plan="undo",
        )
        req = ApprovalRequest(
            approval_id="a1",
            action_type="place_order",
            target_ref_type="order",
            target_ref_id="o1",
            required_count=1,
            state=ApprovalState.PENDING,
            created_by_actor_type="agent",
            created_by_actor_id="trade_agent",
            packet=pkt,
        )
        assert req.packet is pkt
        assert req.packet.action == "test"

    def test_request_without_packet(self) -> None:
        req = ApprovalRequest(
            approval_id="a2",
            action_type="test",
            target_ref_type="test",
            target_ref_id="t1",
            required_count=1,
            state=ApprovalState.PENDING,
            created_by_actor_type="user",
            created_by_actor_id="u1",
        )
        assert req.packet is None


class TestApprovalPacketBuilder:
    def test_build_minimal(self) -> None:
        pkt = (
            ApprovalPacketBuilder()
            .action("test")
            .reason("because")
            .rollback_plan("undo")
            .build()
        )
        assert pkt.action == "test"
        assert pkt.is_complete()

    def test_build_full(self) -> None:
        pkt = (
            ApprovalPacketBuilder()
            .action("place_order")
            .reason("Signal confirmed")
            .evidence([{"source": "signal"}])
            .confidence(0.9)
            .uncertainty({"regime": "unknown"})
            .policy_checks(["var_check"])
            .risk_class(RiskClass.D)
            .alternatives(["defer"])
            .expected_impact({"financial": "+500"})
            .rollback_plan("close_position")
            .escalation_triggers(["policy_conflict"])
            .build()
        )
        assert pkt.action == "place_order"
        assert pkt.confidence == 0.9
        assert pkt.risk_class == RiskClass.D
        assert len(pkt.evidence) == 1
        assert len(pkt.escalation_triggers) == 1
        assert pkt.is_complete()

    def test_from_dict(self) -> None:
        data = {
            "action": "test_action",
            "reason": "test_reason",
            "evidence": [{"k": "v"}],
            "confidence": 0.75,
            "uncertainty": {"x": "y"},
            "policy_checks_passed": ["check1"],
            "risk_class": "B",
            "alternatives_considered": ["alt1"],
            "expected_impact": {"key": "val"},
            "rollback_plan": "rollback_action",
            "escalation_triggers": ["trigger1"],
        }
        pkt = ApprovalPacketBuilder.from_dict(data).build()
        assert pkt.action == "test_action"
        assert pkt.risk_class == RiskClass.B
        assert pkt.rollback_plan == "rollback_action"
        assert pkt.is_complete()

    def test_from_dict_defaults(self) -> None:
        pkt = ApprovalPacketBuilder.from_dict({}).build()
        assert pkt.action == ""
        assert pkt.risk_class == RiskClass.C
        assert pkt.confidence == 0.0

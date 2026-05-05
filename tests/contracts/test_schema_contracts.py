"""Contract tests for agent ↔ workflow ↔ MCP schema boundaries (Playbook §19)."""

from __future__ import annotations

from haruquant.execution import ApprovalPacket, ApprovalRequest, ApprovalState, RiskClass
from haruquant.execution import TradeRecord
from observability.trace_model import Trace
from observability.span_model import Span


def test_approval_packet_schema():
    pkt = ApprovalPacket(
        action="test", reason="test", risk_class=RiskClass.C, rollback_plan="undo"
    )
    assert pkt.is_complete()
    assert isinstance(pkt.evidence, list)
    assert isinstance(pkt.escalation_triggers, list)


def test_approval_request_embeds_packet():
    pkt = ApprovalPacket(action="x", reason="y", rollback_plan="z")
    req = ApprovalRequest(
        approval_id="a1", action_type="test", target_ref_type="t",
        target_ref_id="1", required_count=1, state=ApprovalState.PENDING,
        created_by_actor_type="agent", created_by_actor_id="a1", packet=pkt,
    )
    assert req.packet is pkt


def test_trade_record_has_required_fields():
    tr = TradeRecord()
    assert hasattr(tr, "trade_id")
    assert hasattr(tr, "symbol")
    assert hasattr(tr, "open_price")
    assert hasattr(tr, "close_price")


def test_trace_has_required_fields():
    t = Trace()
    for field_name in [
        "trace_id", "session_id", "user_id", "request_id",
        "task_id", "workflow_id", "step_id", "tool_call_id",
        "agent_name", "prompt_version", "model_name", "model_version",
        "latency_ms", "cost", "result_status",
    ]:
        assert hasattr(t, field_name)


def test_span_has_required_fields():
    s = Span()
    for field_name in ["span_id", "parent_span_id", "trace_id", "name", "duration_ms", "status"]:
        assert hasattr(s, field_name)

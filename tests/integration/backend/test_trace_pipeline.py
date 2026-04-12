"""Integration tests for trace → span → persistence pipeline (Playbook §16)."""

from __future__ import annotations

import time

from backend.observability.cost_tracker import CostTracker
from backend.observability.redaction import RedactionRules
from backend.observability.span_model import Span
from backend.observability.trace_model import Trace


def test_trace_span_lifecycle():
    """Full trace with nested spans records all fields correctly."""
    trace = Trace(
        trace_id="t1",
        session_id="s1",
        user_id=42,
        workflow_id="w1",
        agent_name="trade_analyst",
        prompt_version="1.0.0",
        model_name="gpt-4",
        model_version="2024-01",
    )
    trace.start()

    parent_span = Span(span_id="sp1", trace_id="t1", name="planning")
    parent_span.start()
    child_span = Span(span_id="sp2", trace_id="t1", name="tool_call")
    parent_span.add_child(child_span)
    child_span.start()
    time.sleep(0.01)
    child_span.end("ok")
    time.sleep(0.01)
    parent_span.end("ok")

    time.sleep(0.01)
    trace.end()
    trace.cost = 0.05
    trace.result_status = "success"

    assert trace.latency_ms > 0
    assert child_span.duration_ms > 0
    assert parent_span.duration_ms > 0
    assert child_span.parent_span_id == "sp1"
    assert len(parent_span.children) == 1
    assert trace.to_dict()["model_version"] == "2024-01"
    assert trace.to_dict()["prompt_version"] == "1.0.0"


def test_redaction_in_trace_attributes():
    """Redaction rules remove sensitive fields from trace attributes."""
    redactor = RedactionRules()
    trace_attrs = {
        "input_text": "hello world",
        "api_key": "sk-secret123",
        "password": "hunter2",
        "result": "ok",
    }
    redacted = redactor.redact(trace_attrs)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["input_text"] == "hello world"
    assert redacted["result"] == "ok"


def test_cost_tracker_aggregates_across_spans():
    """Cost tracker aggregates input/output tokens and cost across spans."""
    ct = CostTracker(
        cost_per_input_token=0.00001,
        cost_per_output_token=0.00003,
    )
    ct.record("t1", "sp1", "gpt-4", input_tokens=100, output_tokens=50)
    ct.record("t1", "sp2", "gpt-4", input_tokens=200, output_tokens=100)

    total = ct.total_cost("t1")
    expected = (300 * 0.00001) + (150 * 0.00003)
    assert abs(total - expected) < 1e-9

    tokens = ct.total_tokens("t1")
    assert tokens["input"] == 300
    assert tokens["output"] == 150

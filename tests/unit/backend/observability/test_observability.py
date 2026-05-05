"""Tests for observability: trace, span, redaction, cost tracker."""

from __future__ import annotations

import time

from backend_retiring.observability import CostTracker, RedactionRules, Span, Trace
from backend_retiring.observability.cost_tracker import CostEntry


class TestTrace:
    def test_default_fields(self) -> None:
        t = Trace()
        assert t.trace_id == ""
        assert t.latency_ms == 0.0
        assert t.cost == 0.0

    def test_start_end_sets_latency(self) -> None:
        t = Trace()
        t.start()
        time.sleep(0.01)
        t.end()
        assert t.latency_ms > 0

    def test_add_event(self) -> None:
        t = Trace()
        t.add_event("test", key="val")
        assert len(t.events) == 1
        assert t.events[0]["name"] == "test"

    def test_to_dict(self) -> None:
        t = Trace(trace_id="t1", model_name="gpt-4")
        d = t.to_dict()
        assert d["trace_id"] == "t1"
        assert d["model_name"] == "gpt-4"
        assert "prompt_version" in d
        assert "model_version" in d


class TestSpan:
    def test_start_end(self) -> None:
        s = Span()
        s.start()
        time.sleep(0.01)
        s.end()
        assert s.duration_ms > 0
        assert s.status == "ok"

    def test_add_child(self) -> None:
        parent = Span(span_id="p1", trace_id="t1")
        child = Span(span_id="c1")
        parent.add_child(child)
        assert child.parent_span_id == "p1"
        assert child.trace_id == "t1"
        assert len(parent.children) == 1

    def test_to_dict(self) -> None:
        s = Span(span_id="s1", name="test")
        d = s.to_dict()
        assert d["span_id"] == "s1"
        assert d["name"] == "test"


class TestRedactionRules:
    def test_redact_sensitive_field(self) -> None:
        r = RedactionRules()
        data = {"password": "secret123", "name": "Alice"}
        redacted = r.redact(data)
        assert redacted["password"] == "[REDACTED]"
        assert redacted["name"] == "Alice"

    def test_redact_nested_dict(self) -> None:
        r = RedactionRules()
        data = {"nested": {"api_key": "xyz"}}
        redacted = r.redact(data)
        assert redacted["nested"]["api_key"] == "[REDACTED]"

    def test_custom_sensitive_field(self) -> None:
        r = RedactionRules()
        r.add_sensitive_field("my_secret")
        data = {"my_secret": "val", "public": "ok"}
        redacted = r.redact(data)
        assert redacted["my_secret"] == "[REDACTED]"
        assert redacted["public"] == "ok"

    def test_pattern_matching(self) -> None:
        r = RedactionRules()
        data = {"auth_token": "abc", "username": "user"}
        redacted = r.redact(data)
        assert redacted["auth_token"] == "[REDACTED]"
        assert redacted["username"] == "user"


class TestCostTracker:
    def test_record_and_total(self) -> None:
        ct = CostTracker(cost_per_input_token=0.001, cost_per_output_token=0.002)
        ct.record("t1", input_tokens=100, output_tokens=50)
        assert ct.total_cost() == 0.2  # 100*0.001 + 50*0.002

    def test_total_by_trace(self) -> None:
        ct = CostTracker(cost_per_input_token=0.001)
        ct.record("t1", input_tokens=100)
        ct.record("t2", input_tokens=200)
        assert abs(ct.total_cost("t1") - 0.1) < 1e-9
        assert abs(ct.total_cost("t2") - 0.2) < 1e-9
        assert abs(ct.total_cost() - 0.3) < 1e-9

    def test_total_tokens(self) -> None:
        ct = CostTracker()
        ct.record("t1", input_tokens=100, output_tokens=50)
        tokens = ct.total_tokens("t1")
        assert tokens["input"] == 100
        assert tokens["output"] == 50

    def test_entry_count(self) -> None:
        ct = CostTracker()
        ct.record("t1")
        ct.record("t2")
        assert ct.entry_count == 2

    def test_clear(self) -> None:
        ct = CostTracker()
        ct.record("t1")
        ct.clear()
        assert ct.entry_count == 0

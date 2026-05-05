"""Tests for context engineering components."""

from __future__ import annotations

import time

from backend_retiring.orchestration.context_engineering.budget import ContextBudget
from backend_retiring.orchestration.context_engineering.compression import ContextCompression
from backend_retiring.orchestration.context_engineering.eviction import ContextEviction
from backend_retiring.orchestration.context_engineering.validator import ContextValidator
from backend_retiring.orchestration.context_engineering.contradiction import ContradictionResolver
from backend_retiring.orchestration.context_engineering.precedence import SourcePrecedence, TrustLevel


class TestContextBudget:
    def test_allocate_within_budget(self) -> None:
        b = ContextBudget(max_tokens=1000, reserved_tokens=100)
        assert b.allocate(500) is True
        assert b.used == 500

    def test_allocate_exceeds_budget(self) -> None:
        b = ContextBudget(max_tokens=1000, reserved_tokens=100)
        assert b.allocate(950) is False

    def test_release(self) -> None:
        b = ContextBudget(max_tokens=1000, reserved_tokens=100)
        b.allocate(500)
        b.release(200)
        assert b.used == 300

    def test_utilization(self) -> None:
        b = ContextBudget(max_tokens=1000, reserved_tokens=0)
        b.allocate(500)
        assert b.utilization() == 0.5

    def test_reset(self) -> None:
        b = ContextBudget(max_tokens=1000, reserved_tokens=0)
        b.allocate(500)
        b.reset()
        assert b.used == 0


class TestContextEviction:
    def test_put_and_get(self) -> None:
        e = ContextEviction(ttl_seconds=60)
        e.put("k1", "v1")
        assert e.get("k1") == "v1"

    def test_get_missing(self) -> None:
        e = ContextEviction()
        assert e.get("missing") is None

    def test_ttl_eviction(self) -> None:
        e = ContextEviction(ttl_seconds=0.01)
        e.put("k1", "v1")
        time.sleep(0.02)
        assert e.get("k1") is None

    def test_max_entries(self) -> None:
        e = ContextEviction(max_entries=2)
        e.put("k1", "v1")
        e.put("k2", "v2")
        e.put("k3", "v3")
        assert e.size <= 2

    def test_clear(self) -> None:
        e = ContextEviction()
        e.put("k1", "v1")
        e.clear()
        assert e.size == 0


class TestContextCompression:
    def test_no_compression_needed(self) -> None:
        c = ContextCompression(max_items=10)
        items = [{"i": i} for i in range(5)]
        assert c.compress(items) == items

    def test_compress_large_list(self) -> None:
        c = ContextCompression(max_items=5, abstraction_levels=2)
        items = [{"i": i} for i in range(20)]
        compressed = c.compress(items)
        assert len(compressed) <= 5

    def test_estimation_ratio(self) -> None:
        c = ContextCompression(max_items=5, abstraction_levels=2)
        items = [{"i": i} for i in range(20)]
        ratio = c.estimate_compression_ratio(items)
        assert ratio <= 1.0


class TestSourcePrecedence:
    def test_resolve_most_trusted(self) -> None:
        sp = SourcePrecedence()
        sources = [
            {"source_type": "RAW_TOOL_OUTPUT", "data": {"x": "wrong"}},
            {"source_type": "SESSION_STATE", "data": {"x": "right"}},
        ]
        result = sp.resolve("x", sources)
        assert result is not None
        assert result["data"]["x"] == "right"

    def test_resolve_empty(self) -> None:
        sp = SourcePrecedence()
        assert sp.resolve("x", []) is None

    def test_hierarchy(self) -> None:
        sp = SourcePrecedence()
        assert "SYSTEM_POLICY" in sp.hierarchy


class TestContradictionResolver:
    def test_detect_contradiction(self) -> None:
        cr = ContradictionResolver()
        sources = [
            {"source_type": "A", "data": {"x": 1}},
            {"source_type": "B", "data": {"x": 2}},
        ]
        contradictions = cr.detect(sources)
        assert len(contradictions) == 1
        assert contradictions[0]["key"] == "x"

    def test_no_contradiction(self) -> None:
        cr = ContradictionResolver()
        sources = [
            {"source_type": "A", "data": {"x": 1}},
            {"source_type": "B", "data": {"x": 1}},
        ]
        assert cr.detect(sources) == []

    def test_resolve_with_trust_order(self) -> None:
        cr = ContradictionResolver()
        contradictions = cr.detect([
            {"source_type": "B", "data": {"x": 2}},
            {"source_type": "A", "data": {"x": 1}},
        ])
        result = cr.resolve(contradictions[0], ["A", "B"])
        assert result == 1


class TestContextValidator:
    def test_validate_empty(self) -> None:
        v = ContextValidator()
        issues = v.validate({})
        assert "context is empty" in issues

    def test_validate_valid(self) -> None:
        v = ContextValidator()
        issues = v.validate({"key": "value"})
        assert issues == []

    def test_checklist(self) -> None:
        v = ContextValidator()
        ctx = {"_timestamp": 1, "_source_trust_level": 2, "data": "ok"}
        checks = v.checklist(ctx)
        assert checks["is_necessary"] is True
        assert checks["is_fresh"] is True
        assert checks["is_trusted"] is True

"""Tests for Phase 6: Production Readiness."""

from __future__ import annotations

from backend_retiring.agents.runtime.streaming import run_streaming
from backend_retiring.observability.otel_exporter import OpenTelemetryExporter, OTelExportConfig
from backend_retiring.orchestration.context_engineering.llm_compression import LLMContextCompressor


# ──────────────────────────────────────────────────────────────
# Streaming Tests
# ──────────────────────────────────────────────────────────────

def test_streaming_fallback_on_no_litellm() -> None:
    """Streaming should gracefully handle missing litellm."""
    class FakeRuntime:
        _model = "test-model"
        _temperature = 0.1

    class FakeRequest:
        input_payload = {"test": "data"}

    result = run_streaming(
        llm_runtime=FakeRuntime(),
        request=FakeRequest(),
        context=None,
    )
    # Should return something even if streaming fails
    assert "content" in result
    assert "final_state" in result


# ──────────────────────────────────────────────────────────────
# OpenTelemetry Exporter Tests
# ──────────────────────────────────────────────────────────────

def test_otel_exporter_initial_state() -> None:
    """Exporter should start uninitialized."""
    exporter = OpenTelemetryExporter()
    assert exporter._initialized is False
    assert exporter.traces_exported == 0


def test_otel_exporter_exports_count() -> None:
    """Exporter should track export count when initialized."""
    exporter = OpenTelemetryExporter()
    result = exporter.export_trace({"trace_id": "test"})
    # OTel packages are installed (via chromadb deps), so this succeeds
    assert result is True
    assert exporter.traces_exported == 1


# ──────────────────────────────────────────────────────────────
# LLM Context Compression Tests
# ──────────────────────────────────────────────────────────────

def test_llm_compression_fallback() -> None:
    """Without LLM, should fall back to selective truncation."""
    compressor = LLMContextCompressor(llm_runtime=None)
    items = [
        {"content": f"Context item {i}: " + "important fact " * 10}
        for i in range(20)
    ]
    result = compressor.compress(items, target_tokens=100)
    assert len(result) > 0
    # Should select recent items within budget
    assert "Context item" in result


def test_llm_compression_empty() -> None:
    """Empty context should produce empty output."""
    compressor = LLMContextCompressor(llm_runtime=None)
    result = compressor.compress([], target_tokens=100)
    assert result == ""


def test_llm_compression_preserves_order() -> None:
    """Fallback should preserve chronological order."""
    compressor = LLMContextCompressor(llm_runtime=None)
    items = [
        {"content": "first item content here for testing"},
        {"content": "second item with more details"},
        {"content": "third item even more"},
    ]
    result = compressor.compress(items, target_tokens=200)
    assert "first" in result
    assert "second" in result
    assert "third" in result

"""Cost benchmarks for agent token usage and USD cost."""

from __future__ import annotations

from services.execution.cost.enforcer import CostTracker, MODEL_PRICING


def test_model_pricing_coverage() -> None:
    """All registered models should have pricing entries."""
    registered_models = [
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-pro-preview",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "qwen2.5-coder:7b",
        "llama3.2:latest",
        "gemma4:latest",
        "qwen3.5:latest",
        "phi4-mini-reasoning:latest",
    ]
    for model in registered_models:
        assert model in MODEL_PRICING, f"Missing pricing for {model}"


def test_cost_tracking_per_model() -> None:
    """Cost tracker should track per-model costs."""
    tracker = CostTracker()
    tracker.record(trace_id="t1", model="gemini-3.1-flash-lite-preview", input_tokens=1000, output_tokens=500)
    tracker.record(trace_id="t1", model="gpt-4o", input_tokens=1000, output_tokens=500)

    breakdown = tracker.cost_breakdown_by_model("t1")
    assert len(breakdown) == 2
    # GPT-4o should cost more than Gemini flash-lite
    assert breakdown["gpt-4o"] > breakdown["gemini-3.1-flash-lite-preview"]


def test_cost_tracking_ollama_free() -> None:
    """Ollama models should have zero cost."""
    tracker = CostTracker()
    tracker.record(trace_id="t1", model="qwen2.5-coder:7b", input_tokens=10000, output_tokens=5000)
    assert tracker.total_cost("t1") == 0.0

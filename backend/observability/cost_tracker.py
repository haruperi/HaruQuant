"""Cost tracking per trace and span with model-specific pricing (Playbook §17)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.utils.logger import logger

# ─────────────────────────────────────────────────────────────────────
# Model Pricing Table (per 1M tokens, USD)
# Source: provider pricing pages, updated 2026-04-13
# ─────────────────────────────────────────────────────────────────────

MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Google Gemini
    "gemini-3.1-flash-lite-preview": (0.075, 0.30),
    "gemini-3.1-pro-preview": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-5.4": (2.50, 10.00),
    "gpt-5.4-mini": (1.25, 5.00),
    "gpt-5.4-nano": (0.15, 0.60),
    # Ollama (local models — no API cost)
    "qwen2.5-coder:7b": (0.0, 0.0),
    "llama3.2:latest": (0.0, 0.0),
    "gemma4:latest": (0.0, 0.0),
    "qwen3.5:latest": (0.0, 0.0),
    "phi4-mini-reasoning:latest": (0.0, 0.0),
}


def get_model_pricing(model: str) -> tuple[float, float]:
    """Get (input_rate, output_rate) per 1M tokens for a model.

    Returns (0.0, 0.0) for unknown models with a warning.
    """
    if model not in MODEL_PRICING:
        logger.warning("Unknown model '%s' — defaulting to $0.00 cost", model)
        return (0.0, 0.0)
    return MODEL_PRICING[model]


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a model invocation."""
    input_rate, output_rate = get_model_pricing(model)
    return (input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)


# ─────────────────────────────────────────────────────────────────────
# Cost Tracker
# ─────────────────────────────────────────────────────────────────────

@dataclass
class CostEntry:
    trace_id: str = ""
    span_id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class CostTracker:
    """Track and aggregate costs per trace and span with model-specific pricing."""

    def __init__(
        self,
        cost_per_input_token: float | None = None,
        cost_per_output_token: float | None = None,
    ) -> None:
        self._entries: List[CostEntry] = []
        # Legacy fallback rates (only used if model not in pricing table)
        self._cost_per_input_token = cost_per_input_token or 0.0
        self._cost_per_output_token = cost_per_output_token or 0.0

    def record(
        self,
        trace_id: str,
        span_id: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> CostEntry:
        """Record a cost entry with model-specific pricing."""
        if model and model in MODEL_PRICING:
            cost = calculate_cost(model, input_tokens, output_tokens)
        else:
            # Legacy fallback
            cost = (input_tokens * self._cost_per_input_token) + (output_tokens * self._cost_per_output_token)

        entry = CostEntry(
            trace_id=trace_id,
            span_id=span_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self._entries.append(entry)
        return entry

    def total_cost(self, trace_id: str = "") -> float:
        """Total USD cost, optionally filtered by trace."""
        if trace_id:
            return sum(e.cost_usd for e in self._entries if e.trace_id == trace_id)
        return sum(e.cost_usd for e in self._entries)

    def total_tokens(self, trace_id: str = "") -> Dict[str, int]:
        """Total input/output tokens, optionally filtered by trace."""
        if trace_id:
            entries = [e for e in self._entries if e.trace_id == trace_id]
        else:
            entries = self._entries
        return {
            "input": sum(e.input_tokens for e in entries),
            "output": sum(e.output_tokens for e in entries),
        }

    def cost_breakdown_by_model(self, trace_id: str = "") -> Dict[str, float]:
        """Cost breakdown per model, optionally filtered by trace."""
        if trace_id:
            entries = [e for e in self._entries if e.trace_id == trace_id]
        else:
            entries = self._entries
        breakdown: Dict[str, float] = {}
        for e in entries:
            model = e.model or "unknown"
            breakdown[model] = breakdown.get(model, 0.0) + e.cost_usd
        return breakdown

    def entries(self, trace_id: str = "") -> List[CostEntry]:
        """All cost entries, optionally filtered by trace."""
        if trace_id:
            return [e for e in self._entries if e.trace_id == trace_id]
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

"""Cost enforcement service (Playbook §17).

Enforces cost limits from routing_policy.yaml and tracks per-request
costs against configured budgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml
from pathlib import Path

from services.utils.logger import logger
from config.agent_model import COST_LIMITS, get_model_for_tier


MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-3.1-flash-lite-preview": {"input": 0.0000001, "output": 0.0000004},
    "gemini-3.1-pro-preview": {"input": 0.00000125, "output": 0.00001},
    "gpt-4o": {"input": 0.0000025, "output": 0.00001},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "gpt-5.4": {"input": 0.00000125, "output": 0.00001},
    "gpt-5.4-mini": {"input": 0.00000025, "output": 0.000002},
    "gpt-5.4-nano": {"input": 0.00000005, "output": 0.0000004},
    "qwen2.5-coder:7b": {"input": 0.0, "output": 0.0},
    "llama3.2:latest": {"input": 0.0, "output": 0.0},
    "gemma4:latest": {"input": 0.0, "output": 0.0},
    "qwen3.5:latest": {"input": 0.0, "output": 0.0},
    "phi4-mini-reasoning:latest": {"input": 0.0, "output": 0.0},
}


@dataclass(frozen=True)
class CostEntry:
    trace_id: str
    span_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostTracker:
    """Small in-memory token and cost tracker for cost enforcement."""

    def __init__(
        self,
        *,
        cost_per_input_token: float | None = None,
        cost_per_output_token: float | None = None,
    ) -> None:
        self.cost_per_input_token = cost_per_input_token
        self.cost_per_output_token = cost_per_output_token
        self._entries: list[CostEntry] = []

    def record(
        self,
        trace_id: str,
        span_id: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> CostEntry:
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        input_rate = self.cost_per_input_token if self.cost_per_input_token is not None else pricing["input"]
        output_rate = self.cost_per_output_token if self.cost_per_output_token is not None else pricing["output"]
        entry = CostEntry(
            trace_id=trace_id,
            span_id=span_id,
            model=model,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            cost=(int(input_tokens) * input_rate) + (int(output_tokens) * output_rate),
        )
        self._entries.append(entry)
        return entry

    def total_cost(self, trace_id: str = "") -> float:
        return sum(entry.cost for entry in self._entries if not trace_id or entry.trace_id == trace_id)

    def total_tokens(self, trace_id: str = "") -> dict[str, int]:
        entries = [entry for entry in self._entries if not trace_id or entry.trace_id == trace_id]
        return {
            "input": sum(entry.input_tokens for entry in entries),
            "output": sum(entry.output_tokens for entry in entries),
        }

    def cost_breakdown_by_model(self, trace_id: str = "") -> dict[str, float]:
        breakdown: dict[str, float] = {}
        for entry in self._entries:
            if trace_id and entry.trace_id != trace_id:
                continue
            breakdown[entry.model] = breakdown.get(entry.model, 0.0) + entry.cost
        return breakdown

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

# Load routing policy
_POLICY_PATH = [
    Path(__file__).resolve().parent.parent.parent / "config" / "cost" / "routing_policy.yaml",
]

_global_policy: Optional[Dict[str, Any]] = None


def _load_policy() -> Dict[str, Any]:
    global _global_policy
    if _global_policy is not None:
        return _global_policy
    for path in _POLICY_PATH:
        if path.exists():
            _global_policy = yaml.safe_load(path.read_text()) or {}
            return _global_policy
    _global_policy = {}
    return _global_policy


class CostEnforcer:
    """Enforce cost limits per request, workflow, and session."""

    def __init__(self) -> None:
        self._tracker = CostTracker()
        self._policy = _load_policy()

    def check_request_budget(self, tier: str, estimated_cost: float) -> bool:
        """Check if estimated cost is within the tier budget."""
        routing = self._policy.get("request_routing", {})
        tier_config = routing.get(tier, {})
        max_cost = tier_config.get(
            "max_cost_per_request_usd",
            COST_LIMITS["max_per_request_usd"],
        )
        if estimated_cost > max_cost:
            logger.warning(
                f"CostEnforcer: estimated cost {estimated_cost} exceeds "
                f"tier '{tier}' budget {max_cost}"
            )
            return False
        return True

    def check_workflow_budget(self, current_cost: float) -> bool:
        """Check if cumulative workflow cost is within budget."""
        max_cost = self._policy.get("global_limits", {}).get(
            "max_cost_per_workflow_usd",
            COST_LIMITS["max_per_workflow_usd"],
        )
        if current_cost > max_cost:
            logger.warning(
                f"CostEnforcer: workflow cost {current_cost} exceeds "
                f"budget {max_cost}"
            )
            return False
        return True

    def record_cost(
        self,
        trace_id: str,
        span_id: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record cost for a trace/span."""
        self._tracker.record(
            trace_id=trace_id,
            span_id=span_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def get_current_cost(self, trace_id: str = "") -> float:
        """Get current cumulative cost."""
        return self._tracker.total_cost(trace_id)

    def get_fallback_model(self) -> str:
        """Get the fallback model name from policy."""
        configured = self._policy.get("global_limits", {}).get(
            "fallback_model",
            get_model_for_tier("fallback"),
        )
        if configured in {"lower_cost_model", "fallback_model", "fast_model"}:
            return get_model_for_tier("fallback")
        return str(configured)

    @property
    def tracker(self) -> CostTracker:
        return self._tracker


# Singleton instance
cost_enforcer = CostEnforcer()

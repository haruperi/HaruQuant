"""Cost enforcement service (Playbook §17).

Enforces cost limits from routing_policy.yaml and tracks per-request
costs against configured budgets.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import yaml
from pathlib import Path

from backend.common.logger import logger
from backend.config.agent_model import COST_LIMITS, get_model_for_tier
from backend.observability.cost_tracker import CostTracker

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
        return self._policy.get("global_limits", {}).get(
            "fallback_model",
            get_model_for_tier("fallback"),
        )

    @property
    def tracker(self) -> CostTracker:
        return self._tracker


# Singleton instance
cost_enforcer = CostEnforcer()

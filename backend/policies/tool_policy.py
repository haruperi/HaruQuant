"""Allowlist-based read-only tool policy for AI chat."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: tuple[str, ...]
    denied: tuple[str, ...]
    rationale: str


class ToolPolicy:
    """Enforce allowlist-based tool access per authority band."""

    READ_ONLY_ALLOWLIST = (
        "portfolio_summary",
        "open_positions",
        "backtest_summary",
        "strategy_parameters",
        "optimization_results",
        "risk_snapshot",
        "alert_history",
        "symbol_stats",
    )

    def allow_tools(
        self,
        *,
        requested: tuple[str, ...],
        authority_band: object,
        permission_tier: object = "T1_READ_ONLY",
    ) -> ToolPolicyDecision:
        authority_value = getattr(authority_band, "value", authority_band)
        tier_value = getattr(permission_tier, "value", permission_tier)
        if authority_value != "read_only" or tier_value != "T1_READ_ONLY":
            return ToolPolicyDecision(
                allowed=(),
                denied=requested,
                rationale="Only read-only tool access is enabled in Phase 5.",
            )
        allowed = tuple(tool for tool in requested if tool in self.READ_ONLY_ALLOWLIST)
        denied = tuple(tool for tool in requested if tool not in self.READ_ONLY_ALLOWLIST)
        return ToolPolicyDecision(
            allowed=allowed,
            denied=denied,
            rationale="Allowlist enforced for read-only HaruQuant tools.",
        )

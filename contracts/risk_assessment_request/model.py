from __future__ import annotations

from typing import Literal

from contracts import RequestedFreshnessClasses, RiskAssessmentRequest, RiskAssessmentRequestPayload

FreshnessClass = Literal["HOT", "WARM", "COOL", "COLD"]
KillSwitchState = Literal["ARMED", "SOFT_TRIGGERED", "HARD_TRIGGERED", "RECOVERY_PENDING", "RECOVERY_APPROVED"]
StrategyLifecycleState = Literal[
    "draft",
    "paper_candidate",
    "paper_live",
    "paper_approved",
    "paper_trading_candidate",
    "micro_live",
    "limited_live",
    "normal_live",
    "retired",
]


class ActivePolicyBundle(dict):
    """Backward-compatible adapter for older request assembly code."""

    def __init__(self, *, policy_version: str, formula_version: str | None = None) -> None:
        super().__init__(policy_version=policy_version, formula_version=formula_version)


__all__ = [
    "ActivePolicyBundle",
    "FreshnessClass",
    "KillSwitchState",
    "RequestedFreshnessClasses",
    "RiskAssessmentRequest",
    "RiskAssessmentRequestPayload",
    "StrategyLifecycleState",
]

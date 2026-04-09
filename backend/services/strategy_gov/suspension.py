"""Automatic suspension trigger evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuspensionTriggerRequest:
    drawdown_ratio: float
    unresolved_incident_count: int
    policy_breach_count: int


@dataclass(frozen=True)
class SuspensionTriggerDecision:
    triggered: bool
    reason_codes: tuple[str, ...]


def evaluate_suspension_triggers(
    request: SuspensionTriggerRequest,
    *,
    max_drawdown_ratio: float = 0.2,
    max_unresolved_incidents: int = 1,
    max_policy_breaches: int = 0,
) -> SuspensionTriggerDecision:
    """Evaluate whether a strategy should automatically move to suspended state."""

    reason_codes: list[str] = []
    if request.drawdown_ratio >= max_drawdown_ratio:
        reason_codes.append("drawdown_threshold_breached")
    if request.unresolved_incident_count > max_unresolved_incidents:
        reason_codes.append("incident_threshold_breached")
    if request.policy_breach_count > max_policy_breaches:
        reason_codes.append("policy_breach_threshold_exceeded")

    return SuspensionTriggerDecision(
        triggered=bool(reason_codes),
        reason_codes=tuple(reason_codes),
    )

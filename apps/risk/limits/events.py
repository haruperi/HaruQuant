"""Structured governance events and decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from .models import CircuitBreakerState, GovernanceState, OverrideRecord

Decision = Literal["ACCEPT", "REJECT"]
Severity = Literal["warning", "breach"]


@dataclass(frozen=True)
class LimitEvent:
    """Explainable governance event suitable for later persistence."""

    event_type: str
    rule_key: str
    severity: Severity
    message: str
    observed_value: Optional[float] = None
    threshold_value: Optional[float] = None
    unit: Optional[str] = None
    scope: str = "portfolio"
    scope_key: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyDecision:
    """Structured result from the policy engine."""

    decision: Decision
    reason: str
    breaches: List[LimitEvent] = field(default_factory=list)
    warnings: List[LimitEvent] = field(default_factory=list)
    overrides: List[OverrideRecord] = field(default_factory=list)
    governance_state: Optional[GovernanceState] = None
    circuit_breaker_state: Optional[CircuitBreakerState] = None

    @property
    def policy_events(self) -> List[LimitEvent]:
        return [*self.breaches, *self.warnings]


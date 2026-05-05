"""Circuit-breaker rules for governance state."""

from __future__ import annotations

from typing import Optional, Tuple

from .events import LimitEvent
from .models import CircuitBreakerState, RiskPolicy


def evaluate_circuit_breakers(
    policy: RiskPolicy,
    existing_state: Optional[CircuitBreakerState] = None,
    account_equity: Optional[float] = None,
    peak_equity: Optional[float] = None,
    breach_count: int = 0,
) -> Tuple[Optional[CircuitBreakerState], Optional[LimitEvent]]:
    """Return breaker state and optional breaker breach event."""
    state = existing_state or CircuitBreakerState()

    if policy.max_breach_count is not None and breach_count >= int(policy.max_breach_count):
        return (
            CircuitBreakerState(
                halt_new_risk=True,
                reason="Maximum breach count exceeded.",
                breach_count=breach_count,
            ),
            LimitEvent(
                event_type="circuit_breaker",
                rule_key="breach_count_halt",
                severity="breach",
                message="Circuit breaker triggered by repeated governance breaches.",
                observed_value=float(breach_count),
                threshold_value=float(policy.max_breach_count),
                unit="count",
            ),
        )

    if (
        policy.drawdown_halt_frac is not None
        and account_equity is not None
        and peak_equity is not None
        and peak_equity > 0
    ):
        drawdown = max(0.0, (float(peak_equity) - float(account_equity)) / float(peak_equity))
        if drawdown >= float(policy.drawdown_halt_frac):
            return (
                CircuitBreakerState(
                    halt_new_risk=True,
                    reason="Drawdown circuit breaker triggered.",
                    breach_count=breach_count,
                ),
                LimitEvent(
                    event_type="circuit_breaker",
                    rule_key="drawdown_halt",
                    severity="breach",
                    message="Circuit breaker triggered by account drawdown.",
                    observed_value=float(drawdown),
                    threshold_value=float(policy.drawdown_halt_frac),
                    unit="ratio",
                ),
            )

    return state, None


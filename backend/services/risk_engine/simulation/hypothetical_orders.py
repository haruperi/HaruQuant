"""Hypothetical action helpers for replay what-if analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from backend.services.risk_engine.models import PortfolioState
from backend.services.risk_engine.optimization.marginal_risk import clone_state_with_delta


@dataclass(frozen=True)
class HypotheticalOrderAction:
    """One replay-time hypothetical portfolio action."""

    action_type: str
    symbol: str
    delta_lots: Optional[float] = None
    target_lots: Optional[float] = None
    rationale: str = ""


def resolve_delta(state: PortfolioState, action: HypotheticalOrderAction) -> float:
    """Resolve the signed lot delta for a hypothetical action."""
    current_lots = float(state.position_map.get(action.symbol, 0.0))
    kind = str(action.action_type).strip().lower()

    if action.target_lots is not None:
        return float(action.target_lots) - current_lots

    if kind == "remove":
        return -current_lots

    if action.delta_lots is not None:
        if kind == "reduce":
            return -abs(float(action.delta_lots))
        return float(action.delta_lots)

    if kind == "reduce":
        return -(current_lots * 0.25)

    return 0.0


def apply_hypothetical_actions(
    state: PortfolioState,
    actions: Iterable[HypotheticalOrderAction],
) -> PortfolioState:
    """Apply hypothetical actions to a cloned canonical state."""
    out = state
    for action in actions:
        delta = resolve_delta(out, action)
        out = clone_state_with_delta(
            out,
            symbol=action.symbol,
            delta_lots=delta,
            projected_margin_used=out.account.margin_used,
        )
    return out


def ensure_actions(actions: Iterable[HypotheticalOrderAction]) -> List[HypotheticalOrderAction]:
    return list(actions)

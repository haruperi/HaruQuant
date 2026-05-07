"""UI-ready replay cockpit payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .models import ReplayFrame, WhatIfComparison


@dataclass(frozen=True)
class CockpitStatePayload:
    """Compact payload for simulator cockpit rendering."""

    timestamp: Any
    account: Dict[str, Any]
    positions: List[Dict[str, Any]]
    risk_summary: Dict[str, Any]
    governance: Dict[str, Any]
    regime: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    what_if: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = field(default_factory=dict)


def build_cockpit_state(
    frame: "ReplayFrame",
    what_if: Optional["WhatIfComparison"] = None,
    max_recommendations: int = 3,
) -> CockpitStatePayload:
    """Build a compact replay cockpit payload from one replay frame."""
    account = {
        "equity": frame.state.account.equity,
        "balance": frame.state.account.balance,
        "free_margin": frame.state.account.free_margin,
        "margin_used": frame.state.account.margin_used,
        "currency": frame.state.account.currency,
    }
    positions = [
        {
            "symbol": position.symbol,
            "lots": position.lots,
            "side": position.side,
            "cluster": position.cluster,
            "strategy_id": position.strategy_id,
        }
        for position in frame.state.positions
    ]
    risk_summary = {
        key: frame.snapshot.summary.get(key)
        for key in [
            "portfolio_var",
            "portfolio_es",
            "gross_exposure",
            "net_exposure",
            "current_drawdown",
            "worst_scenario_loss",
            "compliance_state",
        ]
        if key in frame.snapshot.summary
    }
    governance = {
        "decision": frame.snapshot.summary.get("governance_decision"),
        "status": frame.snapshot.summary.get("compliance_state"),
        "reason": frame.snapshot.summary.get("governance_reason"),
        "warnings_count": frame.snapshot.summary.get("governance_warnings_count"),
        "breaches_count": frame.snapshot.summary.get("governance_breaches_count"),
    }
    regime = {
        "name": frame.snapshot.summary.get("regime_name"),
        "confidence": frame.snapshot.summary.get("regime_confidence"),
        "signals_triggered": frame.snapshot.summary.get("regime_signals_triggered"),
    }
    recommendations = []
    if frame.recommendations is not None:
        for item in frame.recommendations.recommendations[:max_recommendations]:
            recommendations.append(
                {
                    "action_type": item.action.action_type,
                    "symbol": item.action.symbol,
                    "delta_lots": item.action.delta_lots,
                    "usefulness_score": item.recommendation_score.usefulness_score,
                    "governance_feasible": item.governance_feasible,
                }
            )
    what_if_payload = None
    if what_if is not None:
        what_if_payload = dict(what_if.summary)

    return CockpitStatePayload(
        timestamp=frame.timestamp,
        account=account,
        positions=positions,
        risk_summary=risk_summary,
        governance=governance,
        regime=regime,
        recommendations=recommendations,
        what_if=what_if_payload,
        context={"frame_index": frame.frame_index},
    )

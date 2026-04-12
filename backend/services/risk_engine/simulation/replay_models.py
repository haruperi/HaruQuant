"""Replay contracts for simulator-backed risk playback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from backend.services.risk_engine.metrics import RiskSnapshot
    from backend.services.risk_engine.models import PortfolioState
    from backend.services.risk_engine.scoring import RiskScorecard
    from backend.services.risk_engine.core.timeline_reconstructor import TimelinePoint
    from backend.services.risk_engine.optimization import RecommendationBatch
    from .cockpit_state import CockpitStatePayload
    from .hypothetical_orders import HypotheticalOrderAction


@dataclass(frozen=True)
class ReplayFrame:
    """One replay frame with normalized risk outputs."""

    frame_index: int
    timestamp: Any
    capture_timestamp: Any
    state: "PortfolioState"
    snapshot: "RiskSnapshot"
    scorecard: "RiskScorecard"
    recommendations: Optional["RecommendationBatch"] = None
    cockpit_state: Optional["CockpitStatePayload"] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayRun:
    """Whole replay output for one simulator-backed run."""

    timeline: List["TimelinePoint"]
    frames: List[ReplayFrame]
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WhatIfComparison:
    """Before/after comparison for one replay-frame hypothetical action set."""

    baseline_frame: ReplayFrame
    actions: List["HypotheticalOrderAction"]
    projected_state: "PortfolioState"
    projected_snapshot: "RiskSnapshot"
    projected_scorecard: "RiskScorecard"
    projected_recommendations: Optional["RecommendationBatch"] = None
    summary: Dict[str, Any] = field(default_factory=dict)

"""Replay what-if analysis built on canonical state and current risk engines."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from services.risk.core import RecommendationEngine, RiskScorecardEngine, RiskSnapshotEngine

from .hypothetical_orders import HypotheticalOrderAction, apply_hypothetical_actions, ensure_actions
from .replay_models import ReplayFrame, WhatIfComparison


class WhatIfEngine:
    """Evaluate hypothetical actions on top of one replay frame."""

    def __init__(
        self,
        snapshot_engine: Optional[RiskSnapshotEngine] = None,
        scorecard_engine: Optional[RiskScorecardEngine] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
    ):
        self.snapshot_engine = snapshot_engine or RiskSnapshotEngine()
        self.scorecard_engine = scorecard_engine or RiskScorecardEngine()
        self.recommendation_engine = recommendation_engine or RecommendationEngine(
            snapshot_engine=self.snapshot_engine,
            scorecard_engine=self.scorecard_engine,
        )

    def evaluate(
        self,
        frame: ReplayFrame,
        actions: Iterable[HypotheticalOrderAction],
        include_recommendations: bool = True,
        candidate_symbols=None,
        hedge_symbols=None,
        max_recommendations: int = 5,
        snapshot_shared: Optional[Dict[str, Any]] = None,
    ) -> WhatIfComparison:
        """Build a before/after comparison for one replay-frame hypothetical."""
        resolved_actions = ensure_actions(actions)
        projected_state = apply_hypothetical_actions(frame.state, resolved_actions)
        projected_snapshot = self.snapshot_engine.build_snapshot(
            projected_state,
            shared=dict(snapshot_shared or {}),
        )
        projected_scorecard = self.scorecard_engine.build_scorecard(projected_snapshot)
        projected_recommendations = None
        if include_recommendations:
            projected_recommendations = self.recommendation_engine.build_recommendations(
                projected_state,
                snapshot=projected_snapshot,
                scorecard=projected_scorecard,
                candidate_symbols=candidate_symbols,
                hedge_symbols=hedge_symbols,
                max_recommendations=max_recommendations,
            )

        baseline_score = float(frame.scorecard.summary.get("overall_risk_quality_score", 0.0) or 0.0)
        projected_score = float(projected_scorecard.summary.get("overall_risk_quality_score", 0.0) or 0.0)
        baseline_var = float(frame.snapshot.summary.get("portfolio_var", 0.0) or 0.0)
        projected_var = float(projected_snapshot.summary.get("portfolio_var", 0.0) or 0.0)
        baseline_es = float(frame.snapshot.summary.get("portfolio_es", 0.0) or 0.0)
        projected_es = float(projected_snapshot.summary.get("portfolio_es", 0.0) or 0.0)

        return WhatIfComparison(
            baseline_frame=frame,
            actions=resolved_actions,
            projected_state=projected_state,
            projected_snapshot=projected_snapshot,
            projected_scorecard=projected_scorecard,
            projected_recommendations=projected_recommendations,
            summary={
                "baseline_overall_score": baseline_score,
                "projected_overall_score": projected_score,
                "overall_score_delta": projected_score - baseline_score,
                "baseline_var": baseline_var,
                "projected_var": projected_var,
                "var_delta": projected_var - baseline_var,
                "baseline_es": baseline_es,
                "projected_es": projected_es,
                "es_delta": projected_es - baseline_es,
            },
        )

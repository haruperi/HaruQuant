"""High-level snapshot persistence helpers."""

from __future__ import annotations

from typing import Optional

from apps.risk.metrics import RiskSnapshot
from apps.risk.optimization import RecommendationBatch
from apps.risk.scoring import RiskScorecard
from apps.risk.simulation import ReplayFrame, WhatIfComparison

from .repositories import RiskRepository


class RiskSnapshotStore:
    """Store and load normalized risk snapshots and closely related artifacts."""

    def __init__(self, repository: RiskRepository):
        self.repository = repository

    def create_run(self, **kwargs) -> int:
        return self.repository.create_run(**kwargs)

    def store_snapshot_bundle(
        self,
        *,
        run_id: int,
        snapshot: RiskSnapshot,
        scorecard: Optional[RiskScorecard] = None,
        recommendations: Optional[RecommendationBatch] = None,
        backtest_id: Optional[int] = None,
    ) -> int:
        snapshot_id = self.repository.db.save_risk_snapshot(
            run_id=run_id,
            snapshot=snapshot,
            backtest_id=backtest_id,
        )
        if scorecard is not None:
            self.repository.db.save_risk_scorecard(
                snapshot_id=snapshot_id,
                scorecard=scorecard,
            )
        if recommendations is not None:
            self.repository.db.save_risk_recommendations(
                snapshot_id=snapshot_id,
                recommendations=recommendations.recommendations,
            )
        return snapshot_id

    def store_replay_frame(
        self,
        *,
        run_id: int,
        frame: ReplayFrame,
        snapshot_id: Optional[int] = None,
        backtest_id: Optional[int] = None,
        what_if: Optional[WhatIfComparison] = None,
    ) -> int:
        return self.repository.db.save_risk_replay_frame(
            run_id=run_id,
            frame=frame,
            snapshot_id=snapshot_id,
            backtest_id=backtest_id,
            what_if=what_if,
        )

    def load_snapshot_bundle(self, snapshot_id: int):
        return self.repository.load_snapshot_bundle(snapshot_id)

    def load_replay_frames(self, run_id: int):
        return self.repository.load_replay_frames(run_id)

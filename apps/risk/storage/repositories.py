"""Thin repository facade over the shared SQLite risk storage mixin."""

from __future__ import annotations

from typing import Any, Optional

from apps.sqlite import SQLiteDatabase


class RiskRepository:
    """Simple repository wrapper that keeps the risk layer SQLite-agnostic."""

    def __init__(self, db: SQLiteDatabase):
        self.db = db

    def create_run(
        self,
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        source: str = "manual",
        backtest_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> int:
        return self.db.create_risk_run(
            label=label,
            description=description,
            source=source,
            backtest_id=backtest_id,
            context=context,
        )

    def load_snapshot_bundle(self, snapshot_id: int) -> dict[str, Any]:
        return self.db.get_risk_snapshot_bundle(snapshot_id)

    def load_replay_frames(self, run_id: int) -> list[dict[str, Any]]:
        return self.db.get_risk_replay_frames(run_id)

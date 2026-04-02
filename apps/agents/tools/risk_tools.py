"""Thin adapters over persisted risk/replay artifacts and safe what-if analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from apps.risk.reports import build_replay_report, build_risk_snapshot_report
from apps.risk.simulation import HypotheticalOrderAction, WhatIfEngine
from apps.sqlite.risk_storage import RiskStorageManager
from apps.simulation.serializers import _serialize_what_if_comparison


class _BoundRiskStorageManager(RiskStorageManager):
    """Provide a concrete constructor for the existing storage helper."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            self.db_path = db_path
            return
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = str(project_root / "data" / "database" / "haruquant.db")


class RiskTools:
    """Expose minimal stored risk/replay reads for early agent workflows."""

    def __init__(
        self,
        manager: Optional[RiskStorageManager] = None,
        *,
        what_if_engine: Optional[WhatIfEngine] = None,
        what_if_serializer: Optional[Callable[[Any], Dict[str, Any]]] = None,
    ) -> None:
        self.manager = manager or _BoundRiskStorageManager()
        self.what_if_engine = what_if_engine or WhatIfEngine()
        self.what_if_serializer = what_if_serializer or _serialize_what_if_comparison

    def risk_get_snapshot_bundle(self, *, snapshot_id: int) -> Dict[str, Any]:
        """Load one stored risk snapshot bundle."""
        return self.manager.get_risk_snapshot_bundle(int(snapshot_id))

    def risk_get_snapshot_report(self, *, snapshot_id: int) -> Dict[str, Any]:
        """Build one machine-readable risk report from storage."""
        bundle = self.manager.get_risk_snapshot_bundle(int(snapshot_id))
        run_id = int(bundle["snapshot"]["run_id"])
        run = self.manager.get_risk_run(run_id)
        return build_risk_snapshot_report(bundle, run=run)

    def replay_get_report(self, *, run_id: int) -> Dict[str, Any]:
        """Build one compact replay report from stored frames."""
        run = self.manager.get_risk_run(int(run_id))
        frames = self.manager.get_risk_replay_frames(int(run_id))
        return build_replay_report(frames, run=run)

    def replay_get_frames(self, *, run_id: int) -> List[Dict[str, Any]]:
        """Return stored replay frames in chronological order."""
        return self.manager.get_risk_replay_frames(int(run_id))

    def risk_export_report(self, *, snapshot_id: int) -> Dict[str, Any]:
        """Export persisted risk snapshot reports to JSON/Markdown artifacts."""
        return self.manager.export_risk_snapshot_reports(int(snapshot_id))

    def replay_export_report(self, *, run_id: int) -> Dict[str, Any]:
        """Export persisted replay reports to JSON/Markdown artifacts."""
        return self.manager.export_risk_replay_report(int(run_id))

    def risk_run_what_if(
        self,
        *,
        frame: Any,
        actions: List[Dict[str, Any]],
        include_recommendations: bool = True,
    ) -> Dict[str, Any]:
        """Run a safe hypothetical comparison on top of one replay frame."""
        resolved_actions = [
            HypotheticalOrderAction(
                action_type=str(item.get("action_type") or "").strip(),
                symbol=str(item.get("symbol") or "").strip().upper(),
                delta_lots=item.get("delta_lots"),
                target_lots=item.get("target_lots"),
                rationale=str(item.get("rationale") or ""),
            )
            for item in actions
            if str(item.get("symbol") or "").strip()
        ]
        comparison = self.what_if_engine.evaluate(
            frame,
            resolved_actions,
            include_recommendations=include_recommendations,
        )
        return self.what_if_serializer(comparison)

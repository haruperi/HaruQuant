"""Thin read-only adapters over persisted risk and replay artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.risk.reports import build_replay_report, build_risk_snapshot_report
from apps.sqlite.risk_storage import RiskStorageManager


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

    def __init__(self, manager: Optional[RiskStorageManager] = None) -> None:
        self.manager = manager or _BoundRiskStorageManager()

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

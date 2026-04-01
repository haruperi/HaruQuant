"""Advisory report export helpers for the agent layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from apps.sqlite.edge_discovery import EdgeDiscoveryManager

from apps.agents.tools.risk_tools import _BoundRiskStorageManager


class ReportTools:
    """Export existing reports or generate small operator artifacts locally."""

    def __init__(
        self,
        *,
        edge_manager: Optional[EdgeDiscoveryManager] = None,
        risk_manager: Optional[_BoundRiskStorageManager] = None,
        base_dir: str | Path = "artifacts/reports/agents",
    ) -> None:
        self.edge_manager = edge_manager or EdgeDiscoveryManager()
        self.risk_manager = risk_manager or _BoundRiskStorageManager()
        self.base_dir = Path(base_dir)

    def edge_export_profile_report(self, *, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Export one stored Edge snapshot report."""
        return self.edge_manager.export_profile_snapshot_reports(int(snapshot_id))

    def risk_export_report(self, *, snapshot_id: int) -> Dict[str, Any]:
        """Export one stored risk snapshot report bundle."""
        return self.risk_manager.export_risk_snapshot_reports(int(snapshot_id))

    def replay_export_report(self, *, run_id: int) -> Dict[str, Any]:
        """Export one stored replay report bundle."""
        return self.risk_manager.export_risk_replay_report(int(run_id))

    def report_generate_json(
        self,
        *,
        report_name: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Write one generic machine-readable JSON artifact."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / f"{report_name}.json"
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return {"artifact_type": "json_report", "artifact_ref": str(path)}

    def report_generate_markdown(
        self,
        *,
        report_name: str,
        content: str,
    ) -> Dict[str, Any]:
        """Write one generic Markdown artifact."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / f"{report_name}.md"
        path.write_text(content, encoding="utf-8")
        return {"artifact_type": "markdown_report", "artifact_ref": str(path)}

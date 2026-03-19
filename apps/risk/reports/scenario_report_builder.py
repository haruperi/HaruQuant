"""Scenario and stress report builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .summary_templates import top_scenarios


def build_scenario_report(
    snapshot_bundle: dict[str, Any],
    *,
    run: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a focused stored-scenario report from one snapshot bundle."""
    snapshot = dict(snapshot_bundle.get("snapshot") or {})
    summary = dict(snapshot.get("summary_json") or {})
    scenarios = top_scenarios(snapshot_bundle.get("scenarios") or [], limit=20)
    worst = scenarios[0] if scenarios else {}
    return {
        "generated_at": datetime.now().isoformat(),
        "run": run,
        "snapshot_id": snapshot.get("snapshot_id"),
        "as_of": snapshot.get("as_of"),
        "worst_scenario_name": worst.get("scenario_name") or summary.get("worst_scenario_name"),
        "worst_scenario_loss": worst.get("loss") or summary.get("worst_scenario_loss"),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }

"""Machine-readable risk snapshot report builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .summary_templates import top_metric_rows, top_recommendations, top_scenarios, top_score_rows


def build_risk_snapshot_report(
    snapshot_bundle: dict[str, Any],
    *,
    run: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build one machine-readable report from a stored snapshot bundle."""
    snapshot = dict(snapshot_bundle.get("snapshot") or {})
    summary = dict(snapshot.get("summary_json") or {})
    governance = dict(snapshot.get("governance_state_json") or {})
    regime_report = dict(snapshot.get("regime_state_json") or {})
    regime_current = dict(regime_report.get("current") or {})

    return {
        "generated_at": datetime.now().isoformat(),
        "run": run,
        "snapshot_header": {
            "snapshot_id": snapshot.get("snapshot_id"),
            "run_id": snapshot.get("run_id"),
            "backtest_id": snapshot.get("backtest_id"),
            "as_of": snapshot.get("as_of"),
            "created_at": snapshot.get("created_at"),
        },
        "portfolio_summary": summary,
        "governance_summary": {
            "status": governance.get("status") or summary.get("compliance_state"),
            "decision": governance.get("decision") or summary.get("governance_decision"),
            "reason": governance.get("reason") or summary.get("governance_reason"),
            "warnings_count": governance.get("warnings_count") or summary.get("governance_warnings_count"),
            "breaches_count": governance.get("breaches_count") or summary.get("governance_breaches_count"),
        },
        "regime_summary": {
            "name": regime_current.get("name") or summary.get("regime_name"),
            "confidence": regime_current.get("confidence") or summary.get("regime_confidence"),
            "signals_triggered": regime_current.get("signals_triggered") or summary.get("regime_signals_triggered") or [],
            "warnings": regime_current.get("warnings") or summary.get("regime_warnings") or [],
        },
        "core_metrics": top_metric_rows(snapshot_bundle.get("metric_rows") or []),
        "scorecard": {
            "summary": _build_score_summary(snapshot_bundle.get("score_rows") or []),
            "rows": top_score_rows(snapshot_bundle.get("score_rows") or []),
        },
        "policy_events": list(snapshot_bundle.get("policy_events") or []),
        "scenarios": top_scenarios(snapshot_bundle.get("scenarios") or []),
        "recommendations": top_recommendations(snapshot_bundle.get("recommendations") or []),
        "snapshot_bundle": snapshot_bundle,
    }


def _build_score_summary(score_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_by_key = {row.get("score_key"): row for row in score_rows}
    overall = rows_by_key.get("overall_risk_quality_score") or {}
    return {
        "overall_risk_quality_score": overall.get("score_value"),
        "overall_confidence": overall.get("confidence"),
        "overall_confidence_label": overall.get("confidence_label"),
        "score_count": len(score_rows),
    }

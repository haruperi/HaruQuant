"""Reporting helpers for full Edge Lab profile snapshots."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_profile_summary(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build a concise dashboard-ready summary from one snapshot."""
    scorecard_summary = dict(snapshot.get("scorecard_summary") or {})
    market_summary = dict((snapshot.get("market_structure_summary") or {}).get("summary") or {})
    unsupervised_summary = dict((snapshot.get("unsupervised_summary") or {}).get("summary") or {})
    unsupervised_risk = dict((snapshot.get("unsupervised_summary") or {}).get("risk_context") or {})
    seasonality_summary = dict(snapshot.get("seasonality_summary") or {})
    best_sessions = list((seasonality_summary.get("opportunity_windows") or {}).get("best_sessions") or [])
    strategy_fit = list(snapshot.get("strategy_fit") or [])

    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "symbol": snapshot.get("symbol"),
        "timeframe": snapshot.get("timeframe"),
        "created_at": snapshot.get("created_at"),
        "model_version": snapshot.get("model_version"),
        "baseline_id": snapshot.get("baseline_id"),
        "final_score": scorecard_summary.get("final_score"),
        "final_label": scorecard_summary.get("final_label"),
        "overall_confidence": scorecard_summary.get("overall_confidence"),
        "score_spec_version": scorecard_summary.get("score_spec_version"),
        "research_ready": scorecard_summary.get("research_ready"),
        "readiness_label": scorecard_summary.get("readiness_label"),
        "readiness_reasons": scorecard_summary.get("readiness_reasons") or [],
        "market_verdict": market_summary.get("verdict"),
        "trend_bias_score": market_summary.get("trend_bias_score"),
        "reversion_bias_score": market_summary.get("reversion_bias_score"),
        "decision_confidence_score": market_summary.get("decision_confidence_score"),
        "best_session": best_sessions[0] if best_sessions else None,
        "primary_strategy_fit": strategy_fit[0] if strategy_fit else None,
        "unsupervised_status": unsupervised_summary.get("status"),
        "unsupervised_cluster_count": unsupervised_summary.get("cluster_count"),
        "unsupervised_top_cluster": unsupervised_risk.get("top_outperforming_cluster"),
        "unsupervised_weakest_cluster": unsupervised_risk.get("weakest_cluster"),
    }


def build_dashboard_summary(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build a UI/dashboard summary block from one snapshot."""
    summary = build_profile_summary(snapshot)
    scores = list(snapshot.get("scores") or [])
    return {
        "header": summary,
        "score_rows": [
            {
                "score_key": row.get("score_key"),
                "label": row.get("label"),
                "score": row.get("score"),
                "confidence": row.get("confidence"),
            }
            for row in scores
        ],
        "warnings": [
            warning
            for row in snapshot.get("strategy_fit") or []
            for warning in (row.get("warnings") or [])[:1]
        ][:5],
    }


def snapshot_report_json(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build a machine-readable complete pair report."""
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": build_profile_summary(snapshot),
        "dashboard_summary": build_dashboard_summary(snapshot),
        "snapshot": snapshot,
    }


def snapshot_report_markdown(snapshot: Dict[str, Any]) -> str:
    """Render one human-readable Markdown pair report."""
    summary = build_profile_summary(snapshot)
    scores = list(snapshot.get("scores") or [])
    strategy_fit = list(snapshot.get("strategy_fit") or [])
    market_summary = dict((snapshot.get("market_structure_summary") or {}).get("summary") or {})
    unsupervised_summary = dict((snapshot.get("unsupervised_summary") or {}).get("summary") or {})
    seasonality_summary = dict(snapshot.get("seasonality_summary") or {})
    best_session = summary.get("best_session") or {}

    lines: List[str] = []
    lines.append(f"# Edge Lab Pair Report: {summary.get('symbol')} {summary.get('timeframe')}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Snapshot ID: {summary.get('snapshot_id')}")
    lines.append(f"Model Version: {summary.get('model_version')}")
    lines.append(f"Baseline ID: {summary.get('baseline_id')}")
    lines.append(f"Score Spec Version: {_fmt(summary.get('score_spec_version'))}")
    lines.append("")
    lines.append("## Profile Summary")
    lines.append("")
    lines.append(f"- Final Score: {_fmt(summary.get('final_score'), 1)}")
    lines.append(f"- Final Label: {_fmt(summary.get('final_label'))}")
    lines.append(f"- Overall Confidence: {_fmt(summary.get('overall_confidence'))}")
    lines.append(f"- Readiness: {_fmt(summary.get('readiness_label'))}")
    lines.append(f"- Market Verdict: {_fmt(summary.get('market_verdict'))}")
    lines.append(f"- Trend Bias: {_fmt(summary.get('trend_bias_score'), 1)}")
    lines.append(f"- Reversion Bias: {_fmt(summary.get('reversion_bias_score'), 1)}")
    lines.append(f"- Decision Confidence: {_fmt(summary.get('decision_confidence_score'), 1)}")
    if summary.get("readiness_reasons"):
        lines.append(f"- Readiness Reasons: {', '.join(summary.get('readiness_reasons') or [])}")
    lines.append("")
    lines.append("## Scorecard")
    lines.append("")
    lines.append("| Score | Value | Confidence | Explanation |")
    lines.append("|------|------:|------------|-------------|")
    for row in scores:
        lines.append(
            f"| {row.get('label')} | {_fmt(row.get('score'), 1)} | {row.get('confidence')} | {row.get('explanation')} |"
        )
    lines.append("")
    lines.append("## Strategy Fit")
    lines.append("")
    lines.append("| Rank | Archetype | Fit | Rationale | Warnings |")
    lines.append("|-----:|-----------|----:|-----------|----------|")
    for row in strategy_fit:
        warnings = ", ".join(row.get("warnings") or []) or "None"
        lines.append(
            f"| {row.get('rank_order')} | {row.get('archetype')} | {_fmt(row.get('fit_score'), 1)} | {row.get('rationale')} | {warnings} |"
        )
    lines.append("")
    lines.append("## Opportunity Windows")
    lines.append("")
    lines.append(f"- Best Session: {_fmt(best_session.get('session'))}")
    lines.append(f"- Best Session Opportunity: {_fmt(best_session.get('opportunity_score'), 1)}")
    lines.append("")
    lines.append("## Unsupervised Structure")
    lines.append("")
    lines.append(f"- Status: {_fmt(summary.get('unsupervised_status'))}")
    lines.append(f"- Cluster Count: {_fmt(summary.get('unsupervised_cluster_count'))}")
    top_cluster = summary.get("unsupervised_top_cluster") or {}
    weakest_cluster = summary.get("unsupervised_weakest_cluster") or {}
    lines.append(f"- Top Cluster: {_fmt(top_cluster.get('cluster_label'))}")
    lines.append(f"- Top Cluster Outperformance: {_fmt(top_cluster.get('outperformance_vs_overall'), 4)}")
    lines.append(f"- Weakest Cluster: {_fmt(weakest_cluster.get('cluster_label'))}")
    if unsupervised_summary.get("pca_explained_variance_ratio"):
        lines.append(
            f"- PCA Variance Ratio: {', '.join(_fmt(value, 4) for value in unsupervised_summary.get('pca_explained_variance_ratio') or [])}"
        )
    lines.append("")
    lines.append("## Market Structure Notes")
    lines.append("")
    lines.append(f"- Breakout Quality: {_fmt((market_summary.get('phase6_commentary') or {}).get('breakout_quality'))}")
    lines.append(f"- Distribution Risk: {_fmt((market_summary.get('phase6_commentary') or {}).get('distribution_risk'))}")
    lines.append(f"- Retracement Profile: {_fmt((market_summary.get('phase6_commentary') or {}).get('retracement_profile'))}")
    lines.append("")
    return "\n".join(lines)


def comparison_report_markdown(comparison: Dict[str, Any]) -> str:
    """Render one Markdown comparison report from two snapshots."""
    left = dict(comparison.get("left_snapshot") or {})
    right = dict(comparison.get("right_snapshot") or {})
    score_diffs = list(comparison.get("score_diffs") or [])
    metric_diffs = list(comparison.get("metric_diffs") or [])

    lines: List[str] = []
    lines.append("# Edge Lab Pair Comparison Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Snapshots")
    lines.append("")
    lines.append(f"- Left: #{left.get('snapshot_id')} {left.get('symbol')} {left.get('timeframe')}")
    lines.append(f"- Right: #{right.get('snapshot_id')} {right.get('symbol')} {right.get('timeframe')}")
    lines.append("")
    lines.append("## Score Differences")
    lines.append("")
    lines.append("| Score | Left | Right |")
    lines.append("|------|-----:|------:|")
    for row in score_diffs:
        lines.append(
            f"| {row.get('label')} | {_fmt(row.get('left_score'), 1)} | {_fmt(row.get('right_score'), 1)} |"
        )
    if not score_diffs:
        lines.append("| None | - | - |")
    lines.append("")
    lines.append("## Key Metric Differences")
    lines.append("")
    lines.append("| Metric | Left | Right |")
    lines.append("|--------|------|-------|")
    for row in metric_diffs[:25]:
        lines.append(
            f"| {row.get('key')} | {_fmt(row.get('left_value'))} | {_fmt(row.get('right_value'))} |"
        )
    if not metric_diffs:
        lines.append("| None | - | - |")
    lines.append("")
    return "\n".join(lines)


def save_json_report(content: Dict[str, Any], path: str | Path) -> Path:
    """Save one complete JSON report."""
    p = Path(path)
    p.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
    return p


def save_markdown_report(content: str, path: str | Path) -> Path:
    """Save one Markdown report."""
    p = Path(path)
    p.write_text(content, encoding="utf-8")
    return p

"""Markdown rendering for risk reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .summary_templates import fmt_value


def render_risk_report_markdown(report: dict[str, Any]) -> str:
    summary = dict(report.get("portfolio_summary") or {})
    governance = dict(report.get("governance_summary") or {})
    regime = dict(report.get("regime_summary") or {})
    lines: list[str] = []
    lines.append(f"# Risk Snapshot Report #{report.get('snapshot_header', {}).get('snapshot_id')}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"As Of: {fmt_value(report.get('snapshot_header', {}).get('as_of'))}")
    lines.append("")
    lines.append("## Portfolio Summary")
    lines.append("")
    lines.append(f"- Gross Exposure: {fmt_value(summary.get('gross_exposure'))}")
    lines.append(f"- Net Exposure: {fmt_value(summary.get('net_exposure'))}")
    lines.append(f"- Portfolio VaR: {fmt_value(summary.get('portfolio_var'))}")
    lines.append(f"- Portfolio ES: {fmt_value(summary.get('portfolio_es'))}")
    lines.append(f"- Current Drawdown: {fmt_value(summary.get('current_drawdown'))}")
    lines.append(f"- Worst Scenario Loss: {fmt_value(summary.get('worst_scenario_loss'))}")
    lines.append("")
    lines.append("## Governance and Regime")
    lines.append("")
    lines.append(f"- Governance Status: {fmt_value(governance.get('status'))}")
    lines.append(f"- Governance Decision: {fmt_value(governance.get('decision'))}")
    lines.append(f"- Governance Reason: {fmt_value(governance.get('reason'))}")
    lines.append(f"- Regime: {fmt_value(regime.get('name'))}")
    lines.append(f"- Regime Confidence: {fmt_value(regime.get('confidence'))}")
    lines.append("")
    lines.append("## Scorecard")
    lines.append("")
    lines.append("| Score | Value | Confidence | Explanation |")
    lines.append("|------|------:|------------|-------------|")
    for row in report.get("scorecard", {}).get("rows", []):
        lines.append(
            f"| {row.get('score_key')} | {fmt_value(row.get('score_value'), 1)} | "
            f"{fmt_value(row.get('confidence_label'))} | {fmt_value(row.get('explanation'))} |"
        )
    lines.append("")
    lines.append("## Stress Scenarios")
    lines.append("")
    lines.append("| Scenario | Loss | Stressed VaR | Stressed ES |")
    lines.append("|----------|-----:|-------------:|------------:|")
    for row in report.get("scenarios", []):
        lines.append(
            f"| {row.get('scenario_name')} | {fmt_value(row.get('loss'))} | "
            f"{fmt_value(row.get('stressed_var'))} | {fmt_value(row.get('stressed_es'))} |"
        )
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    lines.append("| Action | Symbol | Delta Lots | Usefulness | Feasible |")
    lines.append("|--------|--------|-----------:|-----------:|:--------:|")
    for row in report.get("recommendations", []):
        feasible = "Yes" if row.get("governance_feasible") else "No"
        lines.append(
            f"| {row.get('action_type')} | {row.get('symbol')} | {fmt_value(row.get('delta_lots'))} | "
            f"{fmt_value(row.get('usefulness_score'), 1)} | {feasible} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_scenario_report_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Scenario Report #{report.get('snapshot_id')}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"As Of: {fmt_value(report.get('as_of'))}")
    lines.append(f"Worst Scenario: {fmt_value(report.get('worst_scenario_name'))}")
    lines.append(f"Worst Scenario Loss: {fmt_value(report.get('worst_scenario_loss'))}")
    lines.append("")
    lines.append("| Scenario | Loss | Stressed VaR | Stressed ES |")
    lines.append("|----------|-----:|-------------:|------------:|")
    for row in report.get("scenarios", []):
        lines.append(
            f"| {row.get('scenario_name')} | {fmt_value(row.get('loss'))} | "
            f"{fmt_value(row.get('stressed_var'))} | {fmt_value(row.get('stressed_es'))} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_replay_report_markdown(report: dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines: list[str] = []
    lines.append("# Replay Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Frames: {fmt_value(report.get('frame_count'))}")
    lines.append(f"First Timestamp: {fmt_value(report.get('first_timestamp'))}")
    lines.append(f"Last Timestamp: {fmt_value(report.get('last_timestamp'))}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Start Overall Score: {fmt_value(summary.get('start_overall_score'))}")
    lines.append(f"- End Overall Score: {fmt_value(summary.get('end_overall_score'))}")
    lines.append(f"- Last Governance Status: {fmt_value(summary.get('last_governance_status'))}")
    lines.append(f"- Last Regime Name: {fmt_value(summary.get('last_regime_name'))}")
    lines.append(f"- What-If Available: {fmt_value(summary.get('what_if_available'))}")
    lines.append("")
    return "\n".join(lines)

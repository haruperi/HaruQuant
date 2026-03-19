"""Shared formatting and summary helpers for risk reports."""

from __future__ import annotations

from typing import Any, Iterable


def fmt_value(value: Any, digits: int = 2) -> str:
    """Format one value for markdown display."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def top_metric_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the most report-relevant portfolio-level metric rows."""
    keys = {
        "gross_exposure",
        "net_exposure",
        "portfolio_var",
        "portfolio_es",
        "portfolio_realized_volatility",
        "average_pair_correlation",
        "hidden_overlap_score",
        "diversification_ratio",
        "current_drawdown",
        "max_drawdown",
        "worst_scenario_loss",
    }
    return [
        row
        for row in rows
        if row.get("scope") == "portfolio" and row.get("metric_key") in keys
    ]


def top_score_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the score rows ordered as a compact report section."""
    return sorted(rows, key=lambda row: row.get("score_key") or "")


def top_recommendations(rows: Iterable[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Return the top stored recommendations ordered by usefulness."""
    return sorted(
        rows,
        key=lambda row: (
            float(row.get("usefulness_score") or 0.0),
            int(row.get("governance_feasible") or 0),
        ),
        reverse=True,
    )[:limit]


def top_scenarios(rows: Iterable[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Return the worst stored scenarios by loss."""
    return sorted(rows, key=lambda row: float(row.get("loss") or 0.0), reverse=True)[:limit]

"""Drawdown analytics for portfolio risk snapshots."""

from __future__ import annotations

from typing import List

import pandas as pd

from .base import MetricContext, MetricRow


class DrawdownRiskMetrics:
    """Compute drawdown metrics when an equity history is available."""

    family_name = "drawdown_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        equity_records = _resolve_equity_records(context)
        if equity_records is None or equity_records.empty or len(equity_records) < 2:
            return []

        equity_curve = equity_records["equity"].astype(float)
        equity_curve = equity_curve.astype(float)
        running_peak = equity_curve.cummax()
        drawdown = (equity_curve / running_peak) - 1.0
        current_drawdown = float(drawdown.iloc[-1])
        max_drawdown = float(drawdown.min())

        deltas = drawdown.diff().dropna()
        drawdown_velocity = float(deltas.iloc[-1]) if not deltas.empty else 0.0

        if "balance" in equity_records.columns:
            underwater = equity_records["equity"].astype(float) < equity_records["balance"].astype(float)
        else:
            underwater = drawdown < 0.0
        time_under_water = 0
        max_time_under_water = 0
        for value in underwater:
            if bool(value):
                time_under_water += 1
                max_time_under_water = max(max_time_under_water, time_under_water)
            else:
                time_under_water = 0

        return [
            MetricRow(
                self.family_name,
                "current_drawdown",
                "portfolio",
                numeric_value=current_drawdown,
                unit="fraction",
            ),
            MetricRow(
                self.family_name,
                "max_drawdown",
                "portfolio",
                numeric_value=max_drawdown,
                unit="fraction",
            ),
            MetricRow(
                self.family_name,
                "drawdown_velocity",
                "portfolio",
                numeric_value=drawdown_velocity,
                unit="fraction_change",
            ),
            MetricRow(
                self.family_name,
                "time_under_water",
                "portfolio",
                numeric_value=float(max_time_under_water),
                unit="bars",
            ),
        ]


def _resolve_equity_records(context: MetricContext) -> pd.DataFrame | None:
    shared_curve = context.shared.get("equity_curve")
    if isinstance(shared_curve, pd.DataFrame):
        return shared_curve
    if isinstance(shared_curve, pd.Series):
        return pd.DataFrame({"equity": shared_curve.astype(float)})
    normalized_shared = _normalize_equity_curve_records(shared_curve)
    if normalized_shared is not None:
        return normalized_shared

    metadata_curve = context.state.metadata.get("equity_curve")
    if isinstance(metadata_curve, pd.DataFrame):
        return metadata_curve
    if isinstance(metadata_curve, pd.Series):
        return pd.DataFrame({"equity": metadata_curve.astype(float)})
    return _normalize_equity_curve_records(metadata_curve)


def _normalize_equity_curve_records(payload) -> pd.DataFrame | None:
    if not isinstance(payload, list) or not payload:
        return None
    values = []
    for item in payload:
        equity = None
        balance = None
        if isinstance(item, (int, float)):
            equity = float(item)
        elif isinstance(item, dict):
            equity = item.get("equity")
            balance = item.get("balance")
        else:
            equity = getattr(item, "equity", None)
            balance = getattr(item, "balance", None)
        if equity is None:
            continue
        try:
            row = {"equity": float(equity)}
            if balance is not None:
                row["balance"] = float(balance)
            values.append(row)
        except (TypeError, ValueError):
            continue
    if len(values) < 2:
        return None
    return pd.DataFrame(values)

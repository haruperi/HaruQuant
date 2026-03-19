"""Drawdown analytics for portfolio risk snapshots."""

from __future__ import annotations

from typing import List

import pandas as pd

from .base import MetricContext, MetricRow


class DrawdownRiskMetrics:
    """Compute drawdown metrics when an equity history is available."""

    family_name = "drawdown_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        equity_curve = _resolve_equity_curve(context)
        if equity_curve is None or equity_curve.empty or len(equity_curve) < 2:
            return []

        equity_curve = equity_curve.astype(float)
        running_peak = equity_curve.cummax()
        drawdown = (equity_curve / running_peak) - 1.0
        current_drawdown = float(drawdown.iloc[-1])
        max_drawdown = float(drawdown.min())

        deltas = drawdown.diff().dropna()
        drawdown_velocity = float(deltas.iloc[-1]) if not deltas.empty else 0.0

        underwater = drawdown < 0.0
        time_under_water = 0
        for value in reversed(list(underwater)):
            if not bool(value):
                break
            time_under_water += 1

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
                numeric_value=float(time_under_water),
                unit="bars",
            ),
        ]


def _resolve_equity_curve(context: MetricContext) -> pd.Series | None:
    shared_curve = context.shared.get("equity_curve")
    if isinstance(shared_curve, pd.Series):
        return shared_curve

    metadata_curve = context.state.metadata.get("equity_curve")
    if isinstance(metadata_curve, pd.Series):
        return metadata_curve
    if isinstance(metadata_curve, list) and metadata_curve:
        return pd.Series(metadata_curve, dtype=float)
    return None

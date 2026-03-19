"""Margin and leverage metric family."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import estimate_margin_used, symbol_notional_value


class MarginRiskMetrics:
    """Compute current margin and leverage style metrics."""

    family_name = "margin_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        margin_used = estimate_margin_used(context.state)
        gross_exposure = sum(
            abs(symbol_notional_value(context.state, position.symbol, position.lots))
            for position in context.state.positions
        )
        equity = float(context.state.account.equity)

        if margin_used is not None:
            rows.append(
                MetricRow(
                    self.family_name,
                    "margin_used",
                    "portfolio",
                    numeric_value=float(margin_used),
                    unit="currency",
                )
            )
            if equity > 0:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "margin_used_frac",
                        "portfolio",
                        numeric_value=float(margin_used / equity),
                        unit="fraction",
                    )
                )

        if equity > 0:
            rows.append(
                MetricRow(
                    self.family_name,
                    "gross_leverage",
                    "portfolio",
                    numeric_value=float(gross_exposure / equity),
                    unit="multiple",
                )
            )
        if context.state.account.free_margin is not None:
            rows.append(
                MetricRow(
                    self.family_name,
                    "free_margin",
                    "portfolio",
                    numeric_value=float(context.state.account.free_margin),
                    unit="currency",
                )
            )
        return rows

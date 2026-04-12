"""Portfolio-level risk metric family."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import compute_portfolio_var_es, symbol_notional_value


class PortfolioRiskMetrics:
    """Compute top-level current-state portfolio risk metrics."""

    family_name = "portfolio_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        gross_exposure = 0.0
        net_exposure = 0.0
        max_single_abs = 0.0

        for position in context.state.positions:
            notional = symbol_notional_value(context.state, position.symbol, position.lots)
            gross_exposure += abs(notional)
            net_exposure += notional
            max_single_abs = max(max_single_abs, abs(notional))

        var_value, es_value, _, artifacts = compute_portfolio_var_es(context.state)
        rows.extend(
            [
                MetricRow(self.family_name, "gross_exposure", "portfolio", numeric_value=float(gross_exposure), unit="currency"),
                MetricRow(self.family_name, "net_exposure", "portfolio", numeric_value=float(net_exposure), unit="currency"),
                MetricRow(self.family_name, "active_symbol_count", "portfolio", numeric_value=float(len(context.state.active_symbols)), unit="count"),
                MetricRow(self.family_name, "portfolio_var", "portfolio", numeric_value=float(var_value), unit="currency"),
                MetricRow(self.family_name, "portfolio_es", "portfolio", numeric_value=float(es_value), unit="currency"),
            ]
        )

        if context.state.account.equity > 0:
            rows.append(
                MetricRow(
                    self.family_name,
                    "gross_exposure_to_equity",
                    "portfolio",
                    numeric_value=float(gross_exposure / context.state.account.equity),
                    unit="fraction",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "max_single_exposure_frac",
                    "portfolio",
                    numeric_value=float(max_single_abs / gross_exposure) if gross_exposure > 0 else 0.0,
                    unit="fraction",
                )
            )

        portfolio_std = float(artifacts.get("portfolio_std", 0.0) or 0.0)
        rows.append(
            MetricRow(
                self.family_name,
                "portfolio_std",
                "portfolio",
                numeric_value=portfolio_std,
                unit="fraction",
            )
        )
        return rows

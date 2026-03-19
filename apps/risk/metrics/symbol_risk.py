"""Symbol-level risk metrics."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import compute_portfolio_var_es, symbol_notional_value


class SymbolRiskMetrics:
    """Compute symbol-level exposure, weight, and RC metrics."""

    family_name = "symbol_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        _, _, rc_map, artifacts = compute_portfolio_var_es(context.state)
        portfolio_notional = float(artifacts.get("portfolio_notional", 0.0) or 0.0)

        for position in context.state.positions:
            symbol = position.symbol
            notional = abs(symbol_notional_value(context.state, symbol, position.lots))
            market = context.state.markets.get(symbol)
            weight = (notional / portfolio_notional) if portfolio_notional > 0 else 0.0

            rows.append(
                MetricRow(
                    self.family_name,
                    "gross_notional",
                    "symbol",
                    scope_key=symbol,
                    numeric_value=notional,
                    unit="currency",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "portfolio_weight",
                    "symbol",
                    scope_key=symbol,
                    numeric_value=weight,
                    unit="fraction",
                )
            )
            if rc_map is not None:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "risk_contribution_frac",
                        "symbol",
                        scope_key=symbol,
                        numeric_value=float(rc_map.get(symbol, 0.0)),
                        unit="fraction",
                    )
                )
            if market is not None:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "bar_count",
                        "symbol",
                        scope_key=symbol,
                        numeric_value=float(market.row_count),
                        unit="bars",
                    )
                )
                if market.last_close is not None:
                    rows.append(
                        MetricRow(
                            self.family_name,
                            "last_close",
                            "symbol",
                            scope_key=symbol,
                            numeric_value=float(market.last_close),
                            unit="price",
                        )
                    )
        return rows

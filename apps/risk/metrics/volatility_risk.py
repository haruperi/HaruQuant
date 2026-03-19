"""Volatility analytics for structural portfolio fragility."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import (
    build_notional_vector,
    compute_portfolio_var_es,
    compute_symbol_volatility_state,
)


class VolatilityRiskMetrics:
    """Compute symbol and portfolio volatility fragility metrics."""

    family_name = "volatility_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        _, _, _, artifacts = compute_portfolio_var_es(context.state)
        symbols = list(artifacts.get("symbols", []))
        if not symbols:
            return rows

        limits = context.state.limits
        if limits is None:
            return rows

        returns_df = artifacts.get("returns_df")
        if returns_df is None or getattr(returns_df, "empty", True):
            return rows

        vol_map = compute_symbol_volatility_state(returns_df, symbols, limits)
        notionals = build_notional_vector(context.state, symbols, exclude_current_bar=True)
        portfolio_notional = float(artifacts.get("portfolio_notional", 0.0) or 0.0)
        portfolio_std = float(artifacts.get("portfolio_std", 0.0) or 0.0)

        for idx, symbol in enumerate(symbols):
            volatility = float(vol_map.get(symbol, 0.0))
            notional = float(notionals[idx]) if idx < len(notionals) else 0.0
            rows.append(
                MetricRow(
                    self.family_name,
                    "symbol_realized_volatility",
                    "symbol",
                    scope_key=symbol,
                    numeric_value=volatility,
                    unit="return_std",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "vol_adjusted_exposure",
                    "symbol",
                    scope_key=symbol,
                    numeric_value=float(notional * volatility),
                    unit="currency_vol",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "vol_shock_loss_estimate",
                    "symbol",
                    scope_key=symbol,
                    numeric_value=float(notional * volatility * 2.0),
                    unit="currency",
                    context={"shock_sigma": 2.0},
                )
            )

        rows.append(
            MetricRow(
                self.family_name,
                "portfolio_realized_volatility",
                "portfolio",
                numeric_value=portfolio_std,
                unit="return_std",
            )
        )
        rows.append(
            MetricRow(
                self.family_name,
                "portfolio_vol_shock_loss_estimate",
                "portfolio",
                numeric_value=float(portfolio_notional * portfolio_std * 2.0),
                unit="currency",
                context={"shock_sigma": 2.0},
            )
        )
        return rows

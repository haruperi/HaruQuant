"""Tail-risk metrics that wrap the shared portfolio VaR/ES math."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import compute_portfolio_var_es


class TailRiskMetrics:
    """Expose method-tagged VaR/CVaR metrics without changing the existing snapshot keys."""

    family_name = "tail_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        limits = context.state.limits
        if limits is None:
            return []

        var_value, es_value, _, _ = compute_portfolio_var_es(context.state, limits=limits)
        method = "parametric_normal"
        return [
            MetricRow(
                self.family_name,
                "portfolio_var_method",
                "portfolio",
                text_value=method,
            ),
            MetricRow(
                self.family_name,
                "portfolio_cvar_method",
                "portfolio",
                text_value=method,
            ),
            MetricRow(
                self.family_name,
                "portfolio_var_lookback",
                "portfolio",
                numeric_value=float(max(limits.vol_lookback, limits.corr_lookback)),
                unit="bars",
            ),
            MetricRow(
                self.family_name,
                "portfolio_tail_confidence_level",
                "portfolio",
                numeric_value=float(limits.confidence_level),
                unit="fraction",
            ),
            MetricRow(
                self.family_name,
                "portfolio_var_parametric",
                "portfolio",
                numeric_value=float(var_value),
                unit="currency",
            ),
            MetricRow(
                self.family_name,
                "portfolio_cvar_parametric",
                "portfolio",
                numeric_value=float(es_value),
                unit="currency",
            ),
        ]

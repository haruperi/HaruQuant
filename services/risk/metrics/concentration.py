"""Concentration metrics for the current portfolio snapshot."""

from __future__ import annotations

from typing import Dict, List

from .base import MetricContext, MetricRow
from .math import (
    compute_cluster_exposure_breakdown,
    compute_diversification_ratio,
    compute_effective_independent_bets,
    compute_hidden_overlap_score,
    compute_portfolio_var_es,
    symbol_notional_value,
)


class ConcentrationMetrics:
    """Compute simple concentration and cluster concentration metrics."""

    family_name = "concentration"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        _, _, rc_map, artifacts = compute_portfolio_var_es(context.state)

        exposures: Dict[str, float] = {}
        gross_exposure = 0.0
        for position in context.state.positions:
            notional = abs(symbol_notional_value(context.state, position.symbol, position.lots))
            exposures[position.symbol] = notional
            gross_exposure += notional

        if exposures:
            top_symbol = max(exposures.items(), key=lambda item: item[1])
            rows.append(
                MetricRow(
                    self.family_name,
                    "top_symbol_gross_exposure",
                    "portfolio",
                    text_value=top_symbol[0],
                    context={"gross_exposure": float(top_symbol[1])},
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "top_symbol_gross_exposure_frac",
                    "portfolio",
                    numeric_value=float(top_symbol[1] / gross_exposure) if gross_exposure > 0 else 0.0,
                    unit="fraction",
                )
            )

        if rc_map:
            top_rc_symbol = max(rc_map.items(), key=lambda item: item[1])
            rows.append(
                MetricRow(
                    self.family_name,
                    "top_symbol_rc",
                    "portfolio",
                    text_value=top_rc_symbol[0],
                    context={"risk_contribution_frac": float(top_rc_symbol[1])},
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "top_symbol_rc_frac",
                    "portfolio",
                    numeric_value=float(top_rc_symbol[1]),
                    unit="fraction",
                )
            )

        corr_mat = artifacts.get("correlation")
        cov = artifacts.get("covariance")
        weights = artifacts.get("weights")
        if corr_mat is not None and weights is not None:
            rows.append(
                MetricRow(
                    self.family_name,
                    "hidden_overlap_score",
                    "portfolio",
                    numeric_value=compute_hidden_overlap_score(weights, corr_mat),
                    unit="fraction",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "effective_independent_bets",
                    "portfolio",
                    numeric_value=compute_effective_independent_bets(corr_mat),
                    unit="count",
                )
            )
        if cov is not None and weights is not None:
            rows.append(
                MetricRow(
                    self.family_name,
                    "diversification_ratio",
                    "portfolio",
                    numeric_value=compute_diversification_ratio(weights, cov),
                    unit="ratio",
                )
            )

        cluster_gross = compute_cluster_exposure_breakdown(context.state, exclude_current_bar=True)
        gross_cluster_total = float(sum(cluster_gross.values()))
        for cluster, gross in sorted(cluster_gross.items()):
            rows.append(
                MetricRow(
                    self.family_name,
                    "cluster_gross_exposure",
                    "cluster",
                    scope_key=cluster,
                    numeric_value=float(gross),
                    unit="currency",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "cluster_gross_exposure_frac",
                    "cluster",
                    scope_key=cluster,
                    numeric_value=float(gross / gross_cluster_total) if gross_cluster_total > 0.0 else 0.0,
                    unit="fraction",
                )
            )
        return rows

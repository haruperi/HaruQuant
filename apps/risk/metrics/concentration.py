"""Concentration metrics for the current portfolio snapshot."""

from __future__ import annotations

from typing import Dict, List

from .base import MetricContext, MetricRow
from .math import compute_portfolio_var_es, symbol_notional_value


class ConcentrationMetrics:
    """Compute simple concentration and cluster concentration metrics."""

    family_name = "concentration"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        _, _, rc_map, _ = compute_portfolio_var_es(context.state)

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

        cluster_gross: Dict[str, float] = {}
        for position in context.state.positions:
            cluster = position.cluster or context.state.symbol_to_cluster.get(position.symbol)
            if not cluster:
                continue
            cluster_gross[cluster] = cluster_gross.get(cluster, 0.0) + abs(
                symbol_notional_value(context.state, position.symbol, position.lots)
            )

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
        return rows

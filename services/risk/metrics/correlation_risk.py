"""Correlation analytics for structural portfolio fragility."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import (
    average_off_diagonal,
    compute_cluster_correlation_summary,
    compute_hidden_overlap_score,
    compute_portfolio_var_es,
    max_off_diagonal,
)


class CorrelationRiskMetrics:
    """Compute correlation, overlap, and cluster correlation metrics."""

    family_name = "correlation_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        _, _, _, artifacts = compute_portfolio_var_es(context.state)
        symbols = list(artifacts.get("symbols", []))
        corr_mat = artifacts.get("correlation")
        weights = artifacts.get("weights")
        if not symbols or corr_mat is None or weights is None:
            return rows

        for i, left in enumerate(symbols):
            for j in range(i + 1, len(symbols)):
                right = symbols[j]
                rows.append(
                    MetricRow(
                        self.family_name,
                        "pair_correlation",
                        "pair",
                        scope_key=f"{left}:{right}",
                        numeric_value=float(corr_mat[i, j]),
                        unit="correlation",
                    )
                )

        rows.append(
            MetricRow(
                self.family_name,
                "average_pair_correlation",
                "portfolio",
                numeric_value=average_off_diagonal(corr_mat),
                unit="correlation",
            )
        )
        rows.append(
            MetricRow(
                self.family_name,
                "max_pair_correlation",
                "portfolio",
                numeric_value=max_off_diagonal(corr_mat),
                unit="correlation",
            )
        )
        rows.append(
            MetricRow(
                self.family_name,
                "redundancy_score",
                "portfolio",
                numeric_value=compute_hidden_overlap_score(weights, corr_mat),
                unit="fraction",
            )
        )

        cluster_summary = compute_cluster_correlation_summary(
            symbols,
            corr_mat,
            context.state.symbol_to_clusters or context.state.symbol_to_cluster,
        )
        for cluster, summary in sorted(cluster_summary.items()):
            rows.append(
                MetricRow(
                    self.family_name,
                    "cluster_average_correlation",
                    "cluster",
                    scope_key=cluster,
                    numeric_value=float(summary["avg_corr"]),
                    unit="correlation",
                    context={"symbol_count": int(summary["symbol_count"])},
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "cluster_max_correlation",
                    "cluster",
                    scope_key=cluster,
                    numeric_value=float(summary["max_corr"]),
                    unit="correlation",
                    context={"symbol_count": int(summary["symbol_count"])},
                )
            )
        return rows

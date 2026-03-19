"""Orchestration engine for the Phase 2 core risk metric MVP."""

from __future__ import annotations

from typing import Any, Dict, Optional

from apps.risk.metrics import MetricContext, RiskSnapshot
from apps.risk.metrics.registry import MetricRegistry, build_default_metric_registry
from apps.risk.models import PortfolioState


class RiskSnapshotEngine:
    """Build one current-state normalized risk snapshot from PortfolioState."""

    def __init__(self, registry: Optional[MetricRegistry] = None):
        self.registry = registry or build_default_metric_registry()

    def build_snapshot(
        self,
        state: PortfolioState,
        shared: Optional[Dict[str, Any]] = None,
    ) -> RiskSnapshot:
        """Compute all registered metrics and return a normalized snapshot."""
        context = MetricContext(state=state, shared=dict(shared or {}))
        rows = self.registry.compute_all(context)
        summary = self._build_summary(state, rows)
        return RiskSnapshot(state=state, metric_rows=rows, summary=summary)

    def _build_summary(self, state: PortfolioState, rows) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "as_of": state.as_of,
            "active_symbols": state.active_symbols,
            "has_validation_errors": state.validation_summary.has_errors,
            "has_validation_warnings": state.validation_summary.has_warnings,
            "metric_count": len(rows),
        }
        for row in rows:
            if row.scope != "portfolio":
                continue
            if row.metric_key in {
                "gross_exposure",
                "net_exposure",
                "portfolio_var",
                "portfolio_es",
                "gross_exposure_to_equity",
                "gross_leverage",
                "margin_used",
                "margin_used_frac",
            }:
                summary[row.metric_key] = row.numeric_value
        return summary

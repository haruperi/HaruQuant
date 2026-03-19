"""Metric registry for the core risk metric MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .account_risk import AccountRiskMetrics
from .base import MetricContext, MetricFamily, MetricRow
from .concentration import ConcentrationMetrics
from .currency_exposure import CurrencyExposureMetrics
from .margin_risk import MarginRiskMetrics
from .portfolio_risk import PortfolioRiskMetrics
from .position_risk import PositionRiskMetrics
from .strategy_risk import StrategyRiskMetrics
from .symbol_risk import SymbolRiskMetrics


@dataclass
class MetricRegistry:
    """Simple family registry for normalized metric calculation."""

    families: List[MetricFamily] = field(default_factory=list)

    def register(self, family: MetricFamily) -> None:
        self.families.append(family)

    def extend(self, families: Iterable[MetricFamily]) -> None:
        self.families.extend(families)

    def compute_all(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        for family in self.families:
            rows.extend(family.compute(context))
        return rows


def build_default_metric_registry() -> MetricRegistry:
    """Build the default Phase 2 metric family registry."""
    registry = MetricRegistry()
    registry.extend(
        [
            AccountRiskMetrics(),
            PositionRiskMetrics(),
            SymbolRiskMetrics(),
            CurrencyExposureMetrics(),
            StrategyRiskMetrics(),
            PortfolioRiskMetrics(),
            MarginRiskMetrics(),
            ConcentrationMetrics(),
        ]
    )
    return registry

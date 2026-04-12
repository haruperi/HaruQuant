"""Strategy exposure metric family."""

from __future__ import annotations

from typing import Dict, List

from .base import MetricContext, MetricRow
from .math import symbol_notional_value


class StrategyRiskMetrics:
    """Aggregate exposures by strategy identifier when present."""

    family_name = "strategy_exposure"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        grouped: Dict[str, Dict[str, float]] = {}
        for position in context.state.positions:
            if not position.strategy_id:
                continue
            bucket = grouped.setdefault(
                position.strategy_id,
                {"gross_notional": 0.0, "net_notional": 0.0, "position_count": 0.0},
            )
            notional = symbol_notional_value(context.state, position.symbol, position.lots)
            bucket["gross_notional"] += abs(notional)
            bucket["net_notional"] += notional
            bucket["position_count"] += 1.0

        rows: List[MetricRow] = []
        for strategy_id, values in sorted(grouped.items()):
            rows.append(
                MetricRow(
                    self.family_name,
                    "gross_notional",
                    "strategy",
                    scope_key=strategy_id,
                    numeric_value=float(values["gross_notional"]),
                    unit="currency",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "net_notional",
                    "strategy",
                    scope_key=strategy_id,
                    numeric_value=float(values["net_notional"]),
                    unit="currency",
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "position_count",
                    "strategy",
                    scope_key=strategy_id,
                    numeric_value=float(values["position_count"]),
                    unit="count",
                )
            )
        return rows

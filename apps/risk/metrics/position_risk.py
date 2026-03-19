"""Position-level risk metrics."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import symbol_notional_value


class PositionRiskMetrics:
    """Compute one row set per active position."""

    family_name = "position_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        for position in context.state.positions:
            symbol = position.symbol
            notional = symbol_notional_value(context.state, symbol, position.lots)
            market = context.state.markets.get(symbol)
            last_price = market.last_close if market is not None else None

            rows.append(
                MetricRow(
                    self.family_name,
                    "lots",
                    "position",
                    scope_key=symbol,
                    numeric_value=position.lots,
                    unit="lots",
                    context={"side": position.side},
                )
            )
            rows.append(
                MetricRow(
                    self.family_name,
                    "notional_exposure",
                    "position",
                    scope_key=symbol,
                    numeric_value=notional,
                    unit="currency",
                    context={"side": position.side},
                )
            )
            if last_price is not None:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "last_price",
                        "position",
                        scope_key=symbol,
                        numeric_value=last_price,
                        unit="price",
                    )
                )
            if position.entry_price is not None:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "entry_price",
                        "position",
                        scope_key=symbol,
                        numeric_value=position.entry_price,
                        unit="price",
                    )
                )
            if position.cluster:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "cluster",
                        "position",
                        scope_key=symbol,
                        text_value=position.cluster,
                    )
                )
            if position.strategy_id:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "strategy_id",
                        "position",
                        scope_key=symbol,
                        text_value=position.strategy_id,
                    )
                )
        return rows

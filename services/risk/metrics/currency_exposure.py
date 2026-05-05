"""Currency exposure metric family."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow
from .math import extract_currency_exposure


class CurrencyExposureMetrics:
    """Compute simple currency exposure rows from canonical symbol data."""

    family_name = "currency_exposure"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        rows: List[MetricRow] = []
        exposure = extract_currency_exposure(context.state)
        for currency, value in sorted(exposure.items()):
            rows.append(
                MetricRow(
                    self.family_name,
                    "net_currency_exposure",
                    "currency",
                    scope_key=currency,
                    numeric_value=float(value),
                    unit="currency",
                )
            )
        return rows

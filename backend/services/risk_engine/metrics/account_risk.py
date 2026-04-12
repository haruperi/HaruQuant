"""Account state metric family."""

from __future__ import annotations

from typing import List

from .base import MetricContext, MetricRow


class AccountRiskMetrics:
    """Compute account-level current-state risk metrics."""

    family_name = "account_state"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        account = context.state.account
        rows = [
            MetricRow(self.family_name, "equity", "account", numeric_value=account.equity, unit="currency"),
        ]
        if account.balance is not None:
            rows.append(
                MetricRow(self.family_name, "balance", "account", numeric_value=account.balance, unit="currency")
            )
        if account.free_margin is not None:
            rows.append(
                MetricRow(
                    self.family_name,
                    "free_margin",
                    "account",
                    numeric_value=account.free_margin,
                    unit="currency",
                )
            )
        if account.margin_used is not None:
            rows.append(
                MetricRow(
                    self.family_name,
                    "margin_used",
                    "account",
                    numeric_value=account.margin_used,
                    unit="currency",
                )
            )
            if account.equity > 0:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "margin_used_frac",
                        "account",
                        numeric_value=float(account.margin_used / account.equity),
                        unit="fraction",
                    )
                )
        if account.currency:
            rows.append(
                MetricRow(self.family_name, "currency", "account", text_value=account.currency)
            )
        return rows

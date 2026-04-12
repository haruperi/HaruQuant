"""Stress scenario metrics for portfolio snapshots."""

from __future__ import annotations

from typing import List

from backend.services.risk_engine.scenarios import build_default_scenario_registry, evaluate_scenarios

from .base import MetricContext, MetricRow


class StressRiskMetrics:
    """Compute deterministic scenario losses and stressed summaries."""

    family_name = "stress_risk"

    def compute(self, context: MetricContext) -> List[MetricRow]:
        results = evaluate_scenarios(
            context.state,
            registry=context.shared.get("scenario_registry") or build_default_scenario_registry(),
        )
        rows: List[MetricRow] = []
        if not results:
            return rows

        worst = max(results, key=lambda item: item.loss)
        for result in results:
            rows.append(
                MetricRow(
                    self.family_name,
                    "scenario_loss",
                    "scenario",
                    scope_key=result.name,
                    numeric_value=float(result.loss),
                    unit="currency",
                    context=dict(result.context),
                )
            )
            if result.stressed_var is not None:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "stressed_var",
                        "scenario",
                        scope_key=result.name,
                        numeric_value=float(result.stressed_var),
                        unit="currency",
                        context=dict(result.context),
                    )
                )
            if result.stressed_es is not None:
                rows.append(
                    MetricRow(
                        self.family_name,
                        "stressed_es",
                        "scenario",
                        scope_key=result.name,
                        numeric_value=float(result.stressed_es),
                        unit="currency",
                        context=dict(result.context),
                    )
                )

        rows.append(
            MetricRow(
                self.family_name,
                "worst_scenario_loss",
                "portfolio",
                numeric_value=float(worst.loss),
                unit="currency",
            )
        )
        rows.append(
            MetricRow(
                self.family_name,
                "worst_scenario_name",
                "portfolio",
                text_value=worst.name,
            )
        )
        return rows

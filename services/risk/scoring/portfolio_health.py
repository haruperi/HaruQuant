"""Portfolio health score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label, inverse_ratio_score


class PortfolioHealthScore:
    family_name = "portfolio_health"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        summary = context.snapshot.summary
        var_ratio = _ratio(summary.get("portfolio_var"), context.snapshot.state.account.equity)
        es_ratio = _ratio(summary.get("portfolio_es"), context.snapshot.state.account.equity)
        dd_abs = abs(float(summary.get("current_drawdown", 0.0) or 0.0))
        parts = [
            inverse_ratio_score(var_ratio, good=0.03, bad=0.12),
            inverse_ratio_score(es_ratio, good=0.05, bad=0.18),
            inverse_ratio_score(dd_abs, good=0.02, bad=0.15),
        ]
        score = sum(parts) / len(parts)
        confidence = confidence_from_inputs(len(parts))
        return [
            ScoreRow(
                family=self.family_name,
                score_key="portfolio_health_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Combines current drawdown with VaR and CVaR burden versus equity.",
                context={"var_ratio": var_ratio, "es_ratio": es_ratio, "current_drawdown_abs": dd_abs},
            )
        ]


def _ratio(value: float | None, equity: float) -> float | None:
    if value is None or equity <= 0.0:
        return None
    return float(value) / float(equity)

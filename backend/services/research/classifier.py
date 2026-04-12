"""
Edge Classification Logic.

Classifies symbols into:
- Strong Trend Persistence
- Weak Trend Persistence
- Strong Mean Reversion
- Weak Mean Reversion
- Mixed / Regime-Dependent
- No Clear Edge

Based on:
- Expectancy (R)
- Bootstrap CI lower bound
- Sample size
- Relative dominance between MR and TP edges

Also produces:
- Robustness score (0-100)
- Confidence score (0-100)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.services.research.results_schema import EdgeResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MIN_TRADES = 150
DEFAULT_DELTA_R = 0.03
DEFAULT_STRONG_R = 0.08


# ---------------------------------------------------------------------------
# Classification Labels
# ---------------------------------------------------------------------------


class EdgeClass(str, Enum):
    """Enumeration of edge classifications."""

    STRONG_TREND = "Strong Trend Persistence"
    WEAK_TREND = "Weak Trend Persistence"
    STRONG_MEAN_REVERSION = "Strong Mean Reversion"
    WEAK_MEAN_REVERSION = "Weak Mean Reversion"
    MIXED = "Mixed / Regime-Dependent"
    NO_EDGE = "No Clear Edge"


# ---------------------------------------------------------------------------
# Helper Data Container
# ---------------------------------------------------------------------------


@dataclass
class EdgeSummary:
    """Summary of edge metrics."""

    expectancy: float
    ci_low: float
    p_value: Optional[float]
    n_trades: int

    @property
    def is_real(self) -> bool:
        """Check if edge is statistically real.

        Real if:
        - CI lower bound > 0
        - sufficient number of trades
        """
        return self.ci_low > 0 and self.n_trades >= DEFAULT_MIN_TRADES

    @property
    def is_positive(self) -> bool:
        """Check if expectancy is positive."""
        return self.expectancy > 0


@dataclass
class ClassificationResult:
    """Result of the classification process."""

    edge_class: EdgeClass
    robustness: int
    confidence: int
    breakdown: dict


# ---------------------------------------------------------------------------
# Core Classification Function
# ---------------------------------------------------------------------------


def classify_symbol(
    mr: Optional[EdgeResult],
    tp: Optional[EdgeResult],
    *,
    delta_r: float = DEFAULT_DELTA_R,
    strong_r: float = DEFAULT_STRONG_R,
) -> ClassificationResult:
    """
    Classify a symbol based on Mean Reversion (MR) and Trend Persistence (TP) edges.

    Args:
        mr: EdgeResult from EDS-1 (Mean Reversion)
        tp: EdgeResult from EDS-2 (Trend Persistence)

    Returns:
        ClassificationResult
    """
    mr_sum = _to_summary(mr)
    tp_sum = _to_summary(tp)

    if mr_sum is None and tp_sum is None:
        breakdown = _score_breakdown(0, 0, 0, _confidence_bonus(EdgeClass.NO_EDGE))
        return ClassificationResult(
            EdgeClass.NO_EDGE, robustness=0, confidence=0, breakdown=breakdown
        )

    if mr_sum is not None and tp_sum is None:
        edge_class = _classify_single(mr_sum, is_mr=True, strong_r=strong_r)
        components = _robustness_components(mr_sum, strong_r=strong_r)
        robustness = int(components["robustness"])
        bonus = _confidence_bonus(edge_class)
        confidence = _confidence_score(robustness, bonus)
        breakdown = _score_breakdown(
            components["trade_score"],
            components["ci_score"],
            components["exp_score"],
            bonus,
        )
        return ClassificationResult(
            edge_class, robustness, confidence, breakdown=breakdown
        )

    if tp_sum is not None and mr_sum is None:
        edge_class = _classify_single(tp_sum, is_mr=False, strong_r=strong_r)
        components = _robustness_components(tp_sum, strong_r=strong_r)
        robustness = int(components["robustness"])
        bonus = _confidence_bonus(edge_class)
        confidence = _confidence_score(robustness, bonus)
        breakdown = _score_breakdown(
            components["trade_score"],
            components["ci_score"],
            components["exp_score"],
            bonus,
        )
        return ClassificationResult(
            edge_class, robustness, confidence, breakdown=breakdown
        )

    assert mr_sum is not None
    assert tp_sum is not None

    edge_class = _classify_pair(
        mr=mr_sum,
        tp=tp_sum,
        delta_r=delta_r,
        strong_r=strong_r,
    )

    if edge_class == EdgeClass.MIXED:
        mr_components = _robustness_components(mr_sum, strong_r=strong_r)
        tp_components = _robustness_components(tp_sum, strong_r=strong_r)
        components = {
            "trade_score": (mr_components["trade_score"] + tp_components["trade_score"])
            / 2,
            "ci_score": (mr_components["ci_score"] + tp_components["ci_score"]) / 2,
            "exp_score": (mr_components["exp_score"] + tp_components["exp_score"]) / 2,
        }
        robustness = int(
            round(
                components["trade_score"]
                + components["ci_score"]
                + components["exp_score"]
            )
        )
    elif edge_class in (EdgeClass.STRONG_MEAN_REVERSION, EdgeClass.WEAK_MEAN_REVERSION):
        components = _robustness_components(mr_sum, strong_r=strong_r)
        robustness = int(components["robustness"])
    elif edge_class in (EdgeClass.STRONG_TREND, EdgeClass.WEAK_TREND):
        components = _robustness_components(tp_sum, strong_r=strong_r)
        robustness = int(components["robustness"])
    else:
        components = {"trade_score": 0, "ci_score": 0, "exp_score": 0, "robustness": 0}
        robustness = 0

    bonus = _confidence_bonus(edge_class)
    confidence = _confidence_score(robustness, bonus)
    breakdown = _score_breakdown(
        components["trade_score"],
        components["ci_score"],
        components["exp_score"],
        bonus,
    )
    return ClassificationResult(edge_class, robustness, confidence, breakdown=breakdown)


# ---------------------------------------------------------------------------
# Internal Logic
# ---------------------------------------------------------------------------


def _to_summary(res: Optional[EdgeResult]) -> Optional[EdgeSummary]:
    if res is None:
        return None

    stats = res.stats
    return EdgeSummary(
        expectancy=stats.expectancy_r,
        ci_low=stats.ci_low,
        p_value=stats.p_value_perm,
        n_trades=stats.n_trades,
    )


def _classify_single(
    s: EdgeSummary,
    *,
    is_mr: bool,
    strong_r: float,
) -> EdgeClass:
    """Classification when only one edge type is present."""
    if s.is_real and s.expectancy >= strong_r:
        return EdgeClass.STRONG_MEAN_REVERSION if is_mr else EdgeClass.STRONG_TREND

    if s.is_positive:
        return EdgeClass.WEAK_MEAN_REVERSION if is_mr else EdgeClass.WEAK_TREND

    return EdgeClass.NO_EDGE


def _classify_pair(
    *,
    mr: EdgeSummary,
    tp: EdgeSummary,
    delta_r: float,
    strong_r: float,
) -> EdgeClass:
    """Classification when both MR and TP edges exist."""
    if not mr.is_real and not tp.is_real:
        if mr.expectancy > tp.expectancy and mr.is_positive:
            return EdgeClass.WEAK_MEAN_REVERSION
        if tp.expectancy > mr.expectancy and tp.is_positive:
            return EdgeClass.WEAK_TREND
        if mr.is_positive and tp.is_positive:
            return EdgeClass.MIXED
        return EdgeClass.NO_EDGE

    if mr.is_real and tp.is_real:
        diff = mr.expectancy - tp.expectancy

        if diff >= delta_r:
            return (
                EdgeClass.STRONG_MEAN_REVERSION
                if mr.expectancy >= strong_r
                else EdgeClass.WEAK_MEAN_REVERSION
            )

        if diff <= -delta_r:
            return (
                EdgeClass.STRONG_TREND
                if tp.expectancy >= strong_r
                else EdgeClass.WEAK_TREND
            )

        return EdgeClass.MIXED

    if mr.is_real:
        return (
            EdgeClass.STRONG_MEAN_REVERSION
            if mr.expectancy >= strong_r
            else EdgeClass.WEAK_MEAN_REVERSION
        )

    if tp.is_real:
        return (
            EdgeClass.STRONG_TREND
            if tp.expectancy >= strong_r
            else EdgeClass.WEAK_TREND
        )

    return EdgeClass.NO_EDGE


def _robustness_components(summary: EdgeSummary, *, strong_r: float) -> dict:
    trade_score = min(summary.n_trades / DEFAULT_MIN_TRADES, 1.0) * 40.0
    if summary.ci_low > 0:
        ci_score = 40.0
    elif summary.is_positive:
        ci_score = 20.0
    else:
        ci_score = 0.0
    exp_score = min(abs(summary.expectancy) / strong_r, 1.0) * 20.0
    robustness = int(round(min(100.0, trade_score + ci_score + exp_score)))
    return {
        "trade_score": trade_score,
        "ci_score": ci_score,
        "exp_score": exp_score,
        "robustness": robustness,
    }


def _robustness_score(summary: EdgeSummary, *, strong_r: float) -> int:
    return int(_robustness_components(summary, strong_r=strong_r)["robustness"])


def _confidence_bonus(edge_class: EdgeClass) -> int:
    if edge_class in (EdgeClass.STRONG_MEAN_REVERSION, EdgeClass.STRONG_TREND):
        return 10
    if edge_class in (EdgeClass.WEAK_MEAN_REVERSION, EdgeClass.WEAK_TREND):
        return 0
    if edge_class == EdgeClass.MIXED:
        return -5
    return -10


def _confidence_score(robustness: int, bonus: int) -> int:
    return int(max(0, min(100, robustness + bonus)))


def _score_breakdown(
    trade_score: float,
    ci_score: float,
    exp_score: float,
    bonus: int,
) -> dict:
    return {
        "trade_score": int(round(trade_score)),
        "ci_score": int(round(ci_score)),
        "exp_score": int(round(exp_score)),
        "bonus": bonus,
    }

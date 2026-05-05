"""Market Structure engine for directional structure and non-trending behavior."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from services.research.config import (
    BootstrapConfig,
    MeanReversionConfig,
    PermutationConfig,
    TrendPersistenceConfig,
    MarketStructureConfig,
)
from services.research.core_metrics.base import MetricValue
from services.research.data.models import DataQualityReportModel, PreparedDataset
from services.research.market_structure_profiles import (
    resolve_market_structure_profile,
    resolve_market_structure_profile_overrides,
)
from services.research.market_structure_strategy_fit import build_strategy_fit
from services.research.eds_mean_reversion import run_eds_mean_reversion
from services.research.eds_trend_persistence import run_eds_trend_persistence
from services.research.features import atr, bb_width, zscore


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(number) or np.isinf(number):
        return None
    return number


def _metric(key: str, value: Any, **context: Any) -> MetricValue:
    number = _safe_float(value)
    if number is not None:
        return MetricValue(family="market_structure", key=key, value=number, context=context)
    return MetricValue(
        family="market_structure",
        key=key,
        value=str(value) if value is not None else None,
        value_type="text",
        context=context,
    )


def _pip_size(symbol: str) -> float:
    return 0.01 if symbol.upper().endswith("JPY") else 0.0001


def _clip_score(score: float) -> float:
    return float(max(-100.0, min(100.0, score)))


def _normalize_0_100(value: Any, lo: float, hi: float) -> float:
    number = _safe_float(value)
    if number is None or hi <= lo:
        return 0.0
    clipped = max(lo, min(hi, number))
    return float((clipped - lo) / (hi - lo) * 100.0)


def _normalize_minus_100_100(value: Any, lo: float, hi: float) -> float:
    number = _safe_float(value)
    if number is None or hi <= lo:
        return 0.0
    clipped = max(lo, min(hi, number))
    center = (hi + lo) / 2.0
    half_range = (hi - lo) / 2.0
    if half_range <= 0:
        return 0.0
    return float(((clipped - center) / half_range) * 100.0)


def _normalize_penalty(value: Any, lo: float, hi: float) -> float:
    return float(100.0 - _normalize_0_100(value, lo, hi))


@dataclass(frozen=True)
class TrendSwingPoint:
    timestamp: str
    price: float
    swing_type: str
    label: str
    index: int
    atr_value: Optional[float] = None


@dataclass(frozen=True)
class TrendLeg:
    start_time: str
    end_time: str
    direction: str
    amplitude_pips: float
    duration_bars: int
    efficiency_ratio: float
    directional_consistency: float
    pullback_depth: Optional[float] = None
    pullback_duration: Optional[int] = None
    continuation_after_pullback: Optional[bool] = None


@dataclass(frozen=True)
class TrendScoreRow:
    group: str
    key: str
    label: str
    raw_value: Any
    score: float
    weight: float
    contribution: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketStructureProfile:
    symbol: str
    timeframe: str
    data_source: str
    range_by: str
    start_date: Optional[str]
    end_date: Optional[str]
    number_of_bars: Optional[int]
    bar_count: int
    report: DataQualityReportModel
    values: List[MetricValue]
    score_rows: List[TrendScoreRow]
    swing_points: List[TrendSwingPoint]
    trend_legs: List[TrendLeg]
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "data_source": self.data_source,
            "range_by": self.range_by,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "number_of_bars": self.number_of_bars,
            "bar_count": self.bar_count,
            "summary": self.summary,
            "report": {
                "checks_performed": list(self.report.checks_performed),
                "warnings": [asdict(item) for item in self.report.warnings],
                "fatal_errors": [asdict(item) for item in self.report.fatal_errors],
                "cleaning_actions": [asdict(item) for item in self.report.cleaning_actions],
                "metadata": dict(self.report.metadata),
                "is_valid": self.report.is_valid,
            },
            "values": [
                {
                    "family": value.family,
                    "metric_key": value.key,
                    "value": value.value,
                    "value_type": value.value_type,
                    "context": value.context,
                }
                for value in self.values
            ],
            "score_rows": [row.to_dict() for row in self.score_rows],
            "swing_points": [asdict(point) for point in self.swing_points],
            "trend_legs": [asdict(leg) for leg in self.trend_legs],
        }


def _detect_swings(
    data: pd.DataFrame,
    *,
    symbol: str,
    cfg: MarketStructureConfig,
    high_col: str,
    low_col: str,
    close_col: str,
) -> List[TrendSwingPoint]:
    highs = data[high_col].astype(float)
    lows = data[low_col].astype(float)
    close = data[close_col].astype(float)
    atr_series = atr(data, cfg.atr_window, high_col=high_col, low_col=low_col, close_col=close_col)
    pip = _pip_size(symbol)
    window = max(1, int(cfg.swing_window))
    points: List[TrendSwingPoint] = []
    last_price_by_type: Dict[str, float] = {}
    last_index_by_type: Dict[str, int] = {}

    for i in range(window, len(data) - window):
        hi = float(highs.iloc[i])
        lo = float(lows.iloc[i])
        atr_value = _safe_float(atr_series.iloc[i])
        if atr_value is None or atr_value <= 0:
            continue

        is_high = hi >= float(highs.iloc[i - window : i + window + 1].max())
        is_low = lo <= float(lows.iloc[i - window : i + window + 1].min())

        # A single bar can print both local extremes. Treat that as ambiguous
        # rather than manufacturing two swing points from one candle.
        if is_high and is_low:
            continue

        for swing_type, price, active in (("high", hi, is_high), ("low", lo, is_low)):
            if not active:
                continue
            last_price = last_price_by_type.get(swing_type)
            threshold = cfg.min_swing_atr * atr_value
            if last_price is not None and abs(price - last_price) < threshold:
                continue
            if swing_type == "high":
                label = "HH" if last_price is None or price > last_price else "LH"
            else:
                label = "HL" if last_price is None or price > last_price else "LL"
            point = TrendSwingPoint(
                timestamp=data.index[i].isoformat(),
                price=price,
                swing_type=swing_type,
                label=label,
                index=i,
                atr_value=atr_value / pip,
            )
            if last_index_by_type.get(swing_type) == i:
                continue
            points.append(point)
            last_price_by_type[swing_type] = price
            last_index_by_type[swing_type] = i

    points.sort(key=lambda item: item.index)
    deduped: List[TrendSwingPoint] = []
    for point in points:
        if deduped and deduped[-1].index == point.index and deduped[-1].swing_type == point.swing_type:
            continue
        deduped.append(point)
    return deduped


def _direction_from_label(label: str) -> int:
    if label in ("HH", "HL"):
        return 1
    if label in ("LL", "LH"):
        return -1
    return 0


def _build_directional_chains(points: List[TrendSwingPoint]) -> List[Dict[str, Any]]:
    chains: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for point in points:
        direction = _direction_from_label(point.label)
        if direction == 0:
            continue
        if current is None or current["direction"] != direction:
            current = {
                "direction": direction,
                "labels": [point.label],
                "start_time": point.timestamp,
                "end_time": point.timestamp,
            }
            chains.append(current)
            continue
        current["labels"].append(point.label)
        current["end_time"] = point.timestamp
    for chain in chains:
        chain["length"] = len(chain["labels"])
        chain["name"] = "bullish" if chain["direction"] > 0 else "bearish"
    return chains


def _build_legs(
    data: pd.DataFrame,
    *,
    symbol: str,
    points: List[TrendSwingPoint],
    close_col: str,
) -> List[TrendLeg]:
    if len(points) < 2:
        return []
    pip = _pip_size(symbol)
    close = data[close_col].astype(float)
    legs: List[TrendLeg] = []
    for i in range(1, len(points)):
        start = points[i - 1]
        end = points[i]
        if end.index <= start.index:
            continue
        amplitude = end.price - start.price
        direction = "up" if amplitude > 0 else "down" if amplitude < 0 else "flat"
        duration = end.index - start.index
        segment = close.iloc[start.index : end.index + 1]
        net = abs(float(segment.iloc[-1] - segment.iloc[0]))
        path = float(segment.diff().abs().sum())
        efficiency = net / path if path > 0 else 0.0
        directional_moves = segment.diff().dropna()
        if direction == "up":
            consistency = float((directional_moves > 0).mean()) if len(directional_moves) else 0.0
        elif direction == "down":
            consistency = float((directional_moves < 0).mean()) if len(directional_moves) else 0.0
        else:
            consistency = 0.0
        legs.append(
            TrendLeg(
                start_time=start.timestamp,
                end_time=end.timestamp,
                direction=direction,
                amplitude_pips=abs(amplitude) / pip,
                duration_bars=duration,
                efficiency_ratio=efficiency,
                directional_consistency=consistency,
            )
        )

    enriched: List[TrendLeg] = []
    for i, leg in enumerate(legs):
        pullback_depth = None
        pullback_duration = None
        continuation = None
        if 0 < i < len(legs) - 1:
            prev_leg = legs[i - 1]
            next_leg = legs[i + 1]
            if leg.direction != prev_leg.direction and next_leg.direction == prev_leg.direction:
                pullback_depth = (
                    leg.amplitude_pips / prev_leg.amplitude_pips if prev_leg.amplitude_pips > 0 else None
                )
                pullback_duration = leg.duration_bars
                continuation = next_leg.amplitude_pips > leg.amplitude_pips * 0.5
        enriched.append(
            TrendLeg(
                start_time=leg.start_time,
                end_time=leg.end_time,
                direction=leg.direction,
                amplitude_pips=leg.amplitude_pips,
                duration_bars=leg.duration_bars,
                efficiency_ratio=leg.efficiency_ratio,
                directional_consistency=leg.directional_consistency,
                pullback_depth=pullback_depth,
                pullback_duration=pullback_duration,
                continuation_after_pullback=continuation,
            )
        )
    return enriched


def _follow_through_probability(legs: List[TrendLeg]) -> float:
    """Probability that a counter-trend interruption resolves back into prior direction."""
    if len(legs) < 3:
        return 0.0
    opportunities = 0
    continuations = 0
    for i in range(1, len(legs) - 1):
        prev_leg = legs[i - 1]
        current_leg = legs[i]
        next_leg = legs[i + 1]
        if current_leg.direction == "flat" or prev_leg.direction == "flat" or next_leg.direction == "flat":
            continue
        if current_leg.direction != prev_leg.direction:
            opportunities += 1
            if next_leg.direction == prev_leg.direction:
                continuations += 1
    if opportunities == 0:
        return 0.0
    return float(continuations / opportunities)


def _build_score_rows(
    *,
    points: List[TrendSwingPoint],
    chains: List[Dict[str, Any]],
    legs: List[TrendLeg],
    range_metrics: Dict[str, float],
    mr_expectancy: Optional[float],
    mr_confirmed: bool,
    eds_expectancy: Optional[float],
    eds_confirmed: bool,
) -> List[TrendScoreRow]:
    bullish_points = sum(1 for point in points if point.label in ("HH", "HL"))
    bearish_points = sum(1 for point in points if point.label in ("LL", "LH"))
    dominant_bias = bullish_points - bearish_points
    bullish_chains = [chain for chain in chains if chain["direction"] > 0]
    bearish_chains = [chain for chain in chains if chain["direction"] < 0]
    dominant_chains = bullish_chains if dominant_bias >= 0 else bearish_chains
    broken_trends = max(0, len(chains) - 1)

    chain_lengths = [int(chain["length"]) for chain in dominant_chains]
    avg_chain = float(np.mean(chain_lengths)) if chain_lengths else 0.0
    follow_through = _follow_through_probability(legs)

    leg_efficiency = float(np.mean([leg.efficiency_ratio for leg in legs])) if legs else 0.0
    leg_consistency = float(np.mean([leg.directional_consistency for leg in legs])) if legs else 0.0
    pullback_legs = [leg for leg in legs if leg.pullback_depth is not None]
    pullback_depth = float(np.mean([leg.pullback_depth for leg in pullback_legs])) if pullback_legs else 0.0
    pullback_duration = float(np.mean([leg.pullback_duration or 0 for leg in pullback_legs])) if pullback_legs else 0.0
    continuation_rate = float(
        np.mean([1.0 if leg.continuation_after_pullback else 0.0 for leg in pullback_legs])
    ) if pullback_legs else 0.0
    total_points = len(points)
    total_chains = len(chains)
    asymmetry = abs(dominant_bias) / max(1.0, float(total_points))

    direction_sign = 1.0 if dominant_bias >= 0 else -1.0
    rows = [
        TrendScoreRow(
            group="direction",
            key="swing_bias_balance",
            label="Swing Bias Balance",
            raw_value=dominant_bias,
            score=_normalize_minus_100_100(dominant_bias, -10, 10),
            weight=0.18,
            contribution=0.0,
            notes="Balance of bullish vs bearish HH/HL/LL/LH labels.",
        ),
        TrendScoreRow(
            group="direction",
            key="chain_strength",
            label="Chain Strength",
            raw_value=avg_chain,
            score=_normalize_0_100(avg_chain, 1, 5) * direction_sign,
            weight=0.18,
            contribution=0.0,
            notes="Average dominant directional chain length.",
        ),
        TrendScoreRow(
            group="direction",
            key="follow_through_probability",
            label="Follow-Through Probability",
            raw_value=follow_through,
            score=((follow_through * 100.0) - 50.0) * 2.0 * direction_sign,
            weight=0.16,
            contribution=0.0,
            notes="Probability that directional structure keeps extending.",
        ),
        TrendScoreRow(
            group="direction",
            key="pullback_quality",
            label="Pullback Quality",
            raw_value={"depth": pullback_depth, "duration": pullback_duration, "continuation_rate": continuation_rate},
            score=((continuation_rate * 100.0) - (_normalize_0_100(pullback_depth, 0.2, 1.2) * 0.5)) * direction_sign,
            weight=0.20,
            contribution=0.0,
            notes="Shallow pullbacks with strong continuation score better.",
        ),
        TrendScoreRow(
            group="direction",
            key="directional_efficiency",
            label="Directional Efficiency",
            raw_value={"efficiency_ratio": leg_efficiency, "directional_consistency": leg_consistency},
            score=((leg_efficiency * 50.0) + (leg_consistency * 50.0)) * direction_sign,
            weight=0.16,
            contribution=0.0,
            notes="Net travel efficiency and per-bar consistency.",
        ),
        TrendScoreRow(
            group="confidence",
            key="sample_quality",
            label="Sample Quality",
            raw_value={"swing_points": total_points, "chains": total_chains, "pullbacks": len(pullback_legs)},
            score=(
                _normalize_0_100(total_points, 6, 24) * 0.5
                + _normalize_0_100(total_chains, 2, 8) * 0.3
                + _normalize_0_100(len(pullback_legs), 1, 6) * 0.2
            ),
            weight=0.30,
            contribution=0.0,
            notes="More observed structure raises confidence in the estimate.",
        ),
        TrendScoreRow(
            group="confidence",
            key="structural_cleanliness",
            label="Structural Cleanliness",
            raw_value={"broken_trends": broken_trends, "follow_through": follow_through},
            score=(
                _normalize_penalty(broken_trends, 0, 6) * 0.6
                + (follow_through * 100.0) * 0.4
            ),
            weight=0.30,
            contribution=0.0,
            notes="Clean, less-broken structure is more trustworthy.",
        ),
        TrendScoreRow(
            group="confidence",
            key="directional_asymmetry",
            label="Directional Asymmetry",
            raw_value=asymmetry,
            score=asymmetry * 100.0,
            weight=0.15,
            contribution=0.0,
            notes="Confidence rises when one direction clearly dominates.",
        ),
        TrendScoreRow(
            group="confidence",
            key="eds2_confirmation",
            label="EDS-2 Confirmation",
            raw_value={"expectancy_r": eds_expectancy, "confirmed": eds_confirmed},
            score=(
                (_normalize_0_100(abs(eds_expectancy or 0.0), 0.0, 0.5) * 0.5)
                + (50.0 if eds_confirmed else 0.0)
            ),
            weight=0.25,
            contribution=0.0,
            notes="Existing trend-persistence detector adds confirmation, not direction.",
        ),
        TrendScoreRow(
            group="reversion",
            key="range_state_detection",
            label="Range State Detection",
            raw_value={"range_state_rate": range_metrics["range_state_rate"], "range_duration_bars": range_metrics["range_duration_bars"]},
            score=(
                range_metrics["range_state_rate"] * 100.0 * 0.6
                + _normalize_0_100(range_metrics["range_duration_bars"], 3, 20) * 0.4
            ),
            weight=0.22,
            contribution=0.0,
            notes="More persistent bounded behavior supports range bias.",
        ),
        TrendScoreRow(
            group="reversion",
            key="false_break_reentry",
            label="False Break / Reentry",
            raw_value={"false_break_frequency": range_metrics["false_break_frequency"], "reentry_probability": range_metrics["reentry_probability"]},
            score=(
                range_metrics["false_break_frequency"] * 100.0 * 0.5
                + range_metrics["reentry_probability"] * 100.0 * 0.5
            ),
            weight=0.20,
            contribution=0.0,
            notes="Frequent false breaks and reentries support reversion.",
        ),
        TrendScoreRow(
            group="reversion",
            key="mean_reversion_metrics",
            label="Mean Reversion Metrics",
            raw_value={"half_life_bars": range_metrics["half_life_bars"], "zscore_reentry_rate": range_metrics["zscore_reentry_rate"], "band_reentry_rate": range_metrics["band_reentry_rate"]},
            score=(
                _normalize_penalty(range_metrics["half_life_bars"], 2, 30) * 0.3
                + range_metrics["zscore_reentry_rate"] * 100.0 * 0.4
                + range_metrics["band_reentry_rate"] * 100.0 * 0.3
            ),
            weight=0.28,
            contribution=0.0,
            notes="Fast reversion and band/z-score reentry raise reversion bias.",
        ),
        TrendScoreRow(
            group="reversion",
            key="eds1_confirmation",
            label="EDS-1 Confirmation",
            raw_value={"expectancy_r": mr_expectancy, "confirmed": mr_confirmed},
            score=(
                (_normalize_0_100(abs(mr_expectancy or 0.0), 0.0, 0.5) * 0.5)
                + (50.0 if mr_confirmed else 0.0)
            ),
            weight=0.15,
            contribution=0.0,
            notes="Existing mean-reversion detector adds confirmation.",
        ),
        TrendScoreRow(
            group="chop",
            key="choppiness_whipsaw",
            label="Choppiness / Whipsaw",
            raw_value={"choppiness_index": range_metrics["choppiness_index"], "whipsaw_rate": range_metrics["whipsaw_rate"], "direction_flip_rate": range_metrics["direction_flip_rate"]},
            score=(
                _normalize_0_100(range_metrics["choppiness_index"], 35, 65) * 0.4
                + range_metrics["whipsaw_rate"] * 100.0 * 0.35
                + _normalize_0_100(range_metrics["direction_flip_rate"], 0.05, 0.50) * 0.25
            ),
            weight=0.15,
            contribution=0.0,
            notes="High chop and whipsaw reduce trend quality and support non-trending bias.",
        ),
    ]

    finalized: List[TrendScoreRow] = []
    for row in rows:
        contribution = row.score * row.weight
        finalized.append(
            TrendScoreRow(
                group=row.group,
                key=row.key,
                label=row.label,
                raw_value=row.raw_value,
                score=row.score,
                weight=row.weight,
                contribution=contribution,
                notes=row.notes,
            )
        )
    return finalized


def _score_map(rows: List[TrendScoreRow]) -> Dict[str, float]:
    return {row.key: row.score for row in rows}


def _final_verdict(
    trend_bias_score: float,
    reversion_bias_score: float,
    trend_confidence_score: float,
    reversion_confidence_score: float,
    *,
    bias_verdict_min_gap: float,
    trend_confidence_min: float,
    reversion_confidence_min: float,
) -> str:
    if trend_bias_score - reversion_bias_score >= bias_verdict_min_gap:
        if trend_confidence_score < trend_confidence_min:
            return "MIXED"
        return "TREND_BIASED"
    if reversion_bias_score - trend_bias_score >= bias_verdict_min_gap:
        if reversion_confidence_score < reversion_confidence_min:
            return "MIXED"
        return "REVERSION_BIASED"
    return "MIXED"


def _weighted_group_score(rows: List[TrendScoreRow], group: str, *, clip: Optional[float] = None) -> float:
    group_rows = [row for row in rows if row.group == group]
    if not group_rows:
        return 0.0
    total_weight = sum(row.weight for row in group_rows)
    if total_weight <= 0:
        return 0.0
    raw_score = sum(row.contribution for row in group_rows) / total_weight
    if clip is None:
        return raw_score
    return float(max(-clip, min(clip, raw_score)))


def _estimate_half_life(series: pd.Series) -> float:
    clean = series.astype(float).dropna()
    if len(clean) < 20:
        return float("nan")
    lagged = clean.shift(1).dropna()
    delta = clean.diff().dropna()
    aligned = pd.concat([lagged, delta], axis=1).dropna()
    if len(aligned) < 10:
        return float("nan")
    x = aligned.iloc[:, 0].to_numpy(dtype=float)
    y = aligned.iloc[:, 1].to_numpy(dtype=float)
    if np.std(x) == 0:
        return float("nan")
    beta = np.polyfit(x, y, 1)[0]
    if beta >= 0:
        return float("inf")
    return float(-np.log(2.0) / beta)


def _safe_percentile(series: pd.Series, q: float) -> Optional[float]:
    clean = series.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return None
    return float(np.percentile(clean.to_numpy(dtype=float), q))


def _distribution_label(skewness: float, excess_kurtosis: float, jb_stat: float) -> str:
    if not np.isfinite(skewness) or not np.isfinite(excess_kurtosis):
        return "INSUFFICIENT_DATA"
    if abs(skewness) < 0.3 and abs(excess_kurtosis) < 1.0 and jb_stat < 6.0:
        return "APPROX_NORMAL"
    if abs(skewness) >= 0.75 or abs(excess_kurtosis) >= 2.0 or jb_stat >= 20.0:
        return "NON_NORMAL"
    return "MILDLY_NON_NORMAL"


def _phase6_breakout_quality(
    follow_through: float,
    false_break_frequency: float,
    retest_success_rate: float,
) -> str:
    if follow_through >= 0.60 and false_break_frequency <= 0.35 and retest_success_rate >= 0.45:
        return "HIGH"
    if follow_through >= 0.45 and false_break_frequency <= 0.50:
        return "MEDIUM"
    return "LOW"


def _phase6_retracement_label(depth_p50: Optional[float], extension_p75: Optional[float]) -> str:
    if depth_p50 is None or extension_p75 is None:
        return "INSUFFICIENT_DATA"
    if depth_p50 <= 0.75 and extension_p75 >= 1.0:
        return "HEALTHY"
    if depth_p50 <= 1.00:
        return "MIXED"
    return "HEAVY"


def _phase6_excursion_label(study: Dict[str, Any]) -> str:
    target_1r = _safe_float((study.get("target_hit_rates") or {}).get("1.0R"))
    stop_1r = _safe_float((study.get("stop_hit_rates") or {}).get("1.0R"))
    if target_1r is None or stop_1r is None:
        return "INSUFFICIENT_DATA"
    if target_1r >= 0.55 and stop_1r <= 0.40:
        return "FAVORABLE"
    if target_1r >= stop_1r:
        return "BALANCED"
    return "UNFAVORABLE"


def _compute_distribution_metrics(
    data: pd.DataFrame,
    *,
    symbol: str,
    close_col: str,
    high_col: str,
    low_col: str,
) -> Dict[str, Any]:
    close = data[close_col].astype(float)
    high = data[high_col].astype(float)
    low = data[low_col].astype(float)
    pip = _pip_size(symbol)
    returns = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    log_returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
    range_pips = ((high - low) / pip).replace([np.inf, -np.inf], np.nan).dropna()

    if returns.empty:
        return {
            "tail_metrics": {},
            "percentile_tables": {},
            "normality": {"label": "INSUFFICIENT_DATA"},
            "asymmetry": {},
        }

    returns_values = returns.to_numpy(dtype=float)
    mean = float(np.mean(returns_values))
    std = float(np.std(returns_values, ddof=0))
    if std <= 0:
        skewness = 0.0
        excess_kurtosis = 0.0
        jb_stat = 0.0
    else:
        centered = (returns_values - mean) / std
        skewness = float(np.mean(centered ** 3))
        excess_kurtosis = float(np.mean(centered ** 4) - 3.0)
        jb_stat = float((len(returns_values) / 6.0) * ((skewness ** 2) + ((excess_kurtosis ** 2) / 4.0)))

    positive = returns[returns > 0]
    negative = returns[returns < 0]
    upside_tail = _safe_percentile(positive, 95.0) if not positive.empty else None
    downside_tail = abs(_safe_percentile(negative, 5.0) or 0.0) if not negative.empty else None
    tail_balance = None
    if upside_tail is not None and downside_tail not in (None, 0.0):
        tail_balance = float(upside_tail / float(downside_tail))

    return {
        "tail_metrics": {
            "left_tail_p01": _safe_percentile(returns, 1.0),
            "left_tail_p05": _safe_percentile(returns, 5.0),
            "right_tail_p95": _safe_percentile(returns, 95.0),
            "right_tail_p99": _safe_percentile(returns, 99.0),
            "upside_tail_95": upside_tail,
            "downside_tail_05_abs": downside_tail,
        },
        "percentile_tables": {
            "returns": {
                "p05": _safe_percentile(returns, 5.0),
                "p25": _safe_percentile(returns, 25.0),
                "p50": _safe_percentile(returns, 50.0),
                "p75": _safe_percentile(returns, 75.0),
                "p95": _safe_percentile(returns, 95.0),
            },
            "log_returns": {
                "p05": _safe_percentile(log_returns, 5.0),
                "p25": _safe_percentile(log_returns, 25.0),
                "p50": _safe_percentile(log_returns, 50.0),
                "p75": _safe_percentile(log_returns, 75.0),
                "p95": _safe_percentile(log_returns, 95.0),
            },
            "range_pips": {
                "p05": _safe_percentile(range_pips, 5.0),
                "p25": _safe_percentile(range_pips, 25.0),
                "p50": _safe_percentile(range_pips, 50.0),
                "p75": _safe_percentile(range_pips, 75.0),
                "p95": _safe_percentile(range_pips, 95.0),
            },
        },
        "normality": {
            "skewness": skewness,
            "excess_kurtosis": excess_kurtosis,
            "jarque_bera_stat": jb_stat,
            "label": _distribution_label(skewness, excess_kurtosis, jb_stat),
        },
        "asymmetry": {
            "positive_bar_rate": float((returns > 0).mean()),
            "negative_bar_rate": float((returns < 0).mean()),
            "up_down_mean_ratio": float(positive.mean() / abs(negative.mean())) if not positive.empty and not negative.empty and float(abs(negative.mean())) > 0 else None,
            "tail_balance_ratio": tail_balance,
        },
    }


def _compute_range_reversion_metrics(
    data: pd.DataFrame,
    *,
    symbol: str,
    close_col: str,
    high_col: str,
    low_col: str,
    range_window: int = 20,
    breakout_horizon: int = 5,
) -> Dict[str, float]:
    close = data[close_col].astype(float)
    high = data[high_col].astype(float)
    low = data[low_col].astype(float)
    pip = _pip_size(symbol)

    window = max(5, int(range_window))
    upper = high.rolling(window).max()
    lower = low.rolling(window).min()
    prior_upper = upper.shift(1)
    prior_lower = lower.shift(1)
    mid = (upper + lower) / 2.0
    width = upper - lower
    pos = (close - lower) / width.replace(0, np.nan)
    width_pct = (width / close.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    range_state = ((pos >= 0.2) & (pos <= 0.8) & (width_pct <= width_pct.rolling(window).median())).fillna(False)

    segments: List[int] = []
    current = 0
    for active in range_state.to_numpy(dtype=bool):
        if active:
            current += 1
        elif current > 0:
            segments.append(current)
            current = 0
    if current > 0:
        segments.append(current)

    breakout_follow = 0
    false_breaks = 0
    reentries = 0
    breakout_total = 0
    breakout_move_pips: List[float] = []
    false_break_reversal_pips: List[float] = []
    retest_successes = 0
    retest_total = 0
    retracement_depths: List[float] = []
    extensions_pips: List[float] = []
    horizon = max(2, int(breakout_horizon))
    for i in range(window, len(data) - horizon):
        if not np.isfinite(prior_upper.iloc[i]) or not np.isfinite(prior_lower.iloc[i]):
            continue
        px = close.iloc[i]
        up = prior_upper.iloc[i]
        dn = prior_lower.iloc[i]
        if px > up or px < dn:
            breakout_total += 1
            direction = 1 if px > up else -1
            future = close.iloc[i + 1 : i + horizon + 1]
            future_high = high.iloc[i + 1 : i + horizon + 1]
            future_low = low.iloc[i + 1 : i + horizon + 1]
            if len(future) == 0:
                continue
            moved = (future.iloc[-1] - px) * direction
            breakout_move_pips.append(float(moved / pip))
            if moved > 0:
                breakout_follow += 1
            if direction > 0:
                favorable_ext = float((future_high.max() - px) / pip)
                adverse_ext = float((px - future_low.min()) / pip)
            else:
                favorable_ext = float((px - future_low.min()) / pip)
                adverse_ext = float((future_high.max() - px) / pip)
            extensions_pips.append(max(0.0, favorable_ext))
            retracement_depths.append(max(0.0, adverse_ext / max(pip, abs(px - (up if direction > 0 else dn)))))
            if ((future <= up) & (future >= dn)).any():
                reentries += 1
                retest_total += 1
                retest_successes += 1 if favorable_ext > adverse_ext else 0
                if moved <= 0:
                    false_breaks += 1
                    false_break_reversal_pips.append(max(0.0, adverse_ext))

    z = zscore(close, 20)
    bbw = bb_width(close, 20, 2.0)
    z_reentry_total = 0
    z_reentry_hits = 0
    band_reentry_total = 0
    band_reentry_hits = 0
    flip_total = 0
    sign = np.sign(close.diff().fillna(0.0).to_numpy(dtype=float))
    for i in range(20, len(data) - horizon):
        if np.isfinite(z.iloc[i]) and abs(float(z.iloc[i])) >= 2.0:
            z_reentry_total += 1
            future = z.iloc[i + 1 : i + horizon + 1]
            if ((future.abs() <= 0.5)).any():
                z_reentry_hits += 1
        if np.isfinite(pos.iloc[i]) and (pos.iloc[i] < 0.1 or pos.iloc[i] > 0.9):
            band_reentry_total += 1
            future = pos.iloc[i + 1 : i + horizon + 1]
            if ((future >= 0.2) & (future <= 0.8)).any():
                band_reentry_hits += 1
        if i > 1 and sign[i] != 0 and sign[i - 1] != 0 and sign[i] != sign[i - 1]:
            flip_total += 1

    tr = pd.concat(
        [
            (high - low).abs(),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    rolling_tr_sum = tr.rolling(window).sum()
    rolling_range = (upper - lower).replace(0, np.nan)
    choppiness = (
        100.0
        * np.log10(rolling_tr_sum / rolling_range)
        / np.log10(window)
    ).replace([np.inf, -np.inf], np.nan)
    whipsaw_rate = float(false_breaks / breakout_total) if breakout_total else 0.0

    return {
        "range_state_rate": float(range_state.mean()),
        "range_duration_bars": float(np.mean(segments)) if segments else 0.0,
        "range_height_pips": float((width / pip).dropna().mean()) if len(width.dropna()) else 0.0,
        "breakout_follow_probability": float(breakout_follow / breakout_total) if breakout_total else 0.0,
        "false_break_frequency": float(false_breaks / breakout_total) if breakout_total else 0.0,
        "reentry_probability": float(reentries / breakout_total) if breakout_total else 0.0,
        "half_life_bars": _estimate_half_life(close - mid),
        "zscore_reentry_rate": float(z_reentry_hits / z_reentry_total) if z_reentry_total else 0.0,
        "band_reentry_rate": float(band_reentry_hits / band_reentry_total) if band_reentry_total else 0.0,
        "choppiness_index": float(choppiness.dropna().mean()) if len(choppiness.dropna()) else 0.0,
        "whipsaw_rate": whipsaw_rate,
        "direction_flip_rate": float(flip_total / max(1, len(data) - 2)),
        "compression_rate": float((bbw <= bbw.rolling(window).median()).fillna(False).mean()),
        "false_break_reversal_size_pips": float(np.mean(false_break_reversal_pips)) if false_break_reversal_pips else 0.0,
        "retest_success_rate": float(retest_successes / retest_total) if retest_total else 0.0,
        "retracement_depth_distribution": {
            "p25": _safe_percentile(pd.Series(retracement_depths, dtype=float), 25.0),
            "p50": _safe_percentile(pd.Series(retracement_depths, dtype=float), 50.0),
            "p75": _safe_percentile(pd.Series(retracement_depths, dtype=float), 75.0),
            "p95": _safe_percentile(pd.Series(retracement_depths, dtype=float), 95.0),
        },
        "extension_behavior": {
            "avg_extension_pips": float(np.mean(extensions_pips)) if extensions_pips else 0.0,
            "p75_extension_pips": _safe_percentile(pd.Series(extensions_pips, dtype=float), 75.0),
            "p95_extension_pips": _safe_percentile(pd.Series(extensions_pips, dtype=float), 95.0),
            "avg_breakout_move_pips": float(np.mean(breakout_move_pips)) if breakout_move_pips else 0.0,
        },
    }


def _compute_excursion_studies(
    data: pd.DataFrame,
    *,
    symbol: str,
    points: List[TrendSwingPoint],
    legs: List[TrendLeg],
    close_col: str,
    high_col: str,
    low_col: str,
    horizon: int,
) -> Dict[str, Any]:
    pip = _pip_size(symbol)
    close = data[close_col].astype(float)
    high = data[high_col].astype(float)
    low = data[low_col].astype(float)

    event_map: Dict[str, List[Dict[str, float]]] = {"breakout": [], "pullback_resumption": []}
    max_horizon = max(3, int(horizon))

    for point in points:
        if point.index >= len(data) - max_horizon - 1:
            continue
        direction = _direction_from_label(point.label)
        if direction == 0:
            continue
        entry = float(close.iloc[point.index])
        future_high = float(high.iloc[point.index + 1 : point.index + max_horizon + 1].max())
        future_low = float(low.iloc[point.index + 1 : point.index + max_horizon + 1].min())
        future_close = close.iloc[point.index + 1 : point.index + max_horizon + 1]
        if direction > 0:
            mfe = max(0.0, (future_high - entry) / pip)
            mae = max(0.0, (entry - future_low) / pip)
            mfe_series = (high.iloc[point.index + 1 : point.index + max_horizon + 1] - entry) / pip
            mae_series = (entry - low.iloc[point.index + 1 : point.index + max_horizon + 1]) / pip
        else:
            mfe = max(0.0, (entry - future_low) / pip)
            mae = max(0.0, (future_high - entry) / pip)
            mfe_series = (entry - low.iloc[point.index + 1 : point.index + max_horizon + 1]) / pip
            mae_series = (high.iloc[point.index + 1 : point.index + max_horizon + 1] - entry) / pip
        event_map["breakout"].append(
            {
                "mfe": mfe,
                "mae": mae,
                "time_to_mfe": float(int(mfe_series.to_numpy(dtype=float).argmax()) + 1) if len(mfe_series) else 0.0,
                "time_to_mae": float(int(mae_series.to_numpy(dtype=float).argmax()) + 1) if len(mae_series) else 0.0,
            }
        )

    for i, leg in enumerate(legs):
        if not leg.continuation_after_pullback or i + 1 >= len(legs):
            continue
        entry_idx = next((point.index for point in points if point.timestamp == leg.end_time), None)
        if entry_idx is None or entry_idx >= len(data) - max_horizon - 1:
            continue
        direction = 1 if leg.direction == "up" else -1 if leg.direction == "down" else 0
        if direction == 0:
            continue
        entry = float(close.iloc[entry_idx])
        future_high = float(high.iloc[entry_idx + 1 : entry_idx + max_horizon + 1].max())
        future_low = float(low.iloc[entry_idx + 1 : entry_idx + max_horizon + 1].min())
        if direction > 0:
            mfe = max(0.0, (future_high - entry) / pip)
            mae = max(0.0, (entry - future_low) / pip)
            mfe_series = (high.iloc[entry_idx + 1 : entry_idx + max_horizon + 1] - entry) / pip
            mae_series = (entry - low.iloc[entry_idx + 1 : entry_idx + max_horizon + 1]) / pip
        else:
            mfe = max(0.0, (entry - future_low) / pip)
            mae = max(0.0, (future_high - entry) / pip)
            mfe_series = (entry - low.iloc[entry_idx + 1 : entry_idx + max_horizon + 1]) / pip
            mae_series = (high.iloc[entry_idx + 1 : entry_idx + max_horizon + 1] - entry) / pip
        event_map["pullback_resumption"].append(
            {
                "mfe": mfe,
                "mae": mae,
                "time_to_mfe": float(int(mfe_series.to_numpy(dtype=float).argmax()) + 1) if len(mfe_series) else 0.0,
                "time_to_mae": float(int(mae_series.to_numpy(dtype=float).argmax()) + 1) if len(mae_series) else 0.0,
            }
        )

    studies: Dict[str, Any] = {}
    for event_type, rows in event_map.items():
        if not rows:
            studies[event_type] = {
                "count": 0,
                "avg_mfe_pips": None,
                "avg_mae_pips": None,
                "time_to_mfe_bars": None,
                "time_to_mae_bars": None,
                "stop_hit_rates": {},
                "target_hit_rates": {},
            }
            continue
        mfe_values = pd.Series([row["mfe"] for row in rows], dtype=float)
        mae_values = pd.Series([row["mae"] for row in rows], dtype=float)
        stop_hit_rates = {
            "0.5R": float((mae_values >= 0.5).mean()),
            "1.0R": float((mae_values >= 1.0).mean()),
            "1.5R": float((mae_values >= 1.5).mean()),
        }
        target_hit_rates = {
            "0.5R": float((mfe_values >= 0.5).mean()),
            "1.0R": float((mfe_values >= 1.0).mean()),
            "1.5R": float((mfe_values >= 1.5).mean()),
            "2.0R": float((mfe_values >= 2.0).mean()),
        }
        studies[event_type] = {
            "count": len(rows),
            "avg_mfe_pips": float(mfe_values.mean()),
            "avg_mae_pips": float(mae_values.mean()),
            "time_to_mfe_bars": float(np.mean([row["time_to_mfe"] for row in rows])),
            "time_to_mae_bars": float(np.mean([row["time_to_mae"] for row in rows])),
            "stop_hit_rates": stop_hit_rates,
            "target_hit_rates": target_hit_rates,
        }
    return studies


def _average_run_lengths(labels: pd.Series) -> Dict[str, float]:
    durations: Dict[str, List[int]] = {}
    current_label: Optional[str] = None
    current_count = 0
    for label in labels.astype(str).tolist():
        if label == current_label:
            current_count += 1
            continue
        if current_label is not None:
            durations.setdefault(current_label, []).append(current_count)
        current_label = label
        current_count = 1
    if current_label is not None and current_count > 0:
        durations.setdefault(current_label, []).append(current_count)
    return {
        label: float(np.mean(values))
        for label, values in durations.items()
        if values
    }


def _share_map(labels: pd.Series) -> Dict[str, float]:
    if len(labels) == 0:
        return {}
    counts = labels.astype(str).value_counts(normalize=True)
    return {str(key): float(value) for key, value in counts.items()}


def _transition_matrix(labels: pd.Series) -> Dict[str, Dict[str, float]]:
    clean = labels.astype(str).tolist()
    counts: Dict[str, Dict[str, int]] = {}
    for prev, nxt in zip(clean, clean[1:]):
        counts.setdefault(prev, {})
        counts[prev][nxt] = counts[prev].get(nxt, 0) + 1
    matrix: Dict[str, Dict[str, float]] = {}
    for prev, row in counts.items():
        total = sum(row.values())
        matrix[prev] = {
            nxt: float(count / total)
            for nxt, count in row.items()
        } if total > 0 else {}
    return matrix


def _top_regime_metrics(
    frame: pd.DataFrame,
    *,
    group_col: str,
    return_col: str,
    range_col: str,
    spread_col: str,
    volume_col: str,
    top_n: int = 8,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if frame.empty:
        return rows
    grouped = frame.groupby(group_col, dropna=False)
    total = len(frame)
    for label, group in grouped:
        rows.append(
            {
                "regime": str(label),
                "share": float(len(group) / total) if total else 0.0,
                "avg_return": float(group[return_col].mean()) if len(group) else 0.0,
                "avg_abs_return": float(group[return_col].abs().mean()) if len(group) else 0.0,
                "avg_range_pips": float(group[range_col].mean()) if len(group) else 0.0,
                "avg_spread": float(group[spread_col].mean()) if len(group) else 0.0,
                "avg_volume": float(group[volume_col].mean()) if len(group) else 0.0,
            }
        )
    rows.sort(key=lambda item: item["share"], reverse=True)
    return rows[:top_n]


def _compute_regime_engine(
    data: pd.DataFrame,
    *,
    symbol: str,
    close_col: str,
    high_col: str,
    low_col: str,
    volume_col: str,
    spread_col: str,
    cfg: MarketStructureConfig,
) -> Dict[str, Any]:
    close = data[close_col].astype(float)
    high = data[high_col].astype(float)
    low = data[low_col].astype(float)
    volume = data[volume_col].astype(float).fillna(0.0)
    spread = data[spread_col].astype(float).fillna(0.0)
    pip = _pip_size(symbol)

    returns = close.pct_change().fillna(0.0)
    range_pips = ((high - low) / pip).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    atr_series = atr(data, cfg.atr_window, high_col=high_col, low_col=low_col, close_col=close_col).bfill().ffill()
    atr_pips = (atr_series / pip).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    fast_ma = close.rolling(10, min_periods=3).mean()
    slow_ma = close.rolling(30, min_periods=8).mean()
    slow_slope = slow_ma.diff(5).fillna(0.0)
    trend_strength = ((fast_ma - slow_ma).abs() / atr_series.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    trend_regime = pd.Series("neutral", index=data.index, dtype="object")
    trend_regime[(fast_ma > slow_ma) & (slow_slope > 0) & (trend_strength >= 0.25)] = "bullish_trend"
    trend_regime[(fast_ma < slow_ma) & (slow_slope < 0) & (trend_strength >= 0.25)] = "bearish_trend"
    trend_regime[trend_strength <= 0.12] = "range"

    atr_low = float(atr_pips.quantile(0.33)) if len(atr_pips) else 0.0
    atr_high = float(atr_pips.quantile(0.67)) if len(atr_pips) else 0.0
    volatility_regime = pd.Series("normal_vol", index=data.index, dtype="object")
    volatility_regime[atr_pips <= atr_low] = "low_vol"
    volatility_regime[atr_pips >= atr_high] = "high_vol"

    volume_low = float(volume.quantile(0.33)) if len(volume) else 0.0
    volume_high = float(volume.quantile(0.67)) if len(volume) else 0.0
    spread_low = float(spread.quantile(0.33)) if len(spread) else 0.0
    spread_high = float(spread.quantile(0.67)) if len(spread) else 0.0
    liquidity_regime = pd.Series("normal_liquidity", index=data.index, dtype="object")
    liquidity_regime[(volume >= volume_high) & (spread <= spread_low)] = "high_liquidity"
    liquidity_regime[(volume <= volume_low) | (spread >= spread_high)] = "low_liquidity"

    combined = (
        trend_regime.astype(str)
        + "|"
        + volatility_regime.astype(str)
        + "|"
        + liquidity_regime.astype(str)
    )

    frame = pd.DataFrame(
        {
            "trend_regime": trend_regime,
            "volatility_regime": volatility_regime,
            "liquidity_regime": liquidity_regime,
            "combined_regime": combined,
            "returns": returns,
            "range_pips": range_pips,
            "spread": spread,
            "volume": volume,
        },
        index=data.index,
    )

    regime_score_inputs = {
        "trend_share": float(((trend_regime == "bullish_trend") | (trend_regime == "bearish_trend")).mean()),
        "range_share": float((trend_regime == "range").mean()),
        "high_vol_trend_share": float((((trend_regime == "bullish_trend") | (trend_regime == "bearish_trend")) & (volatility_regime == "high_vol")).mean()),
        "low_vol_range_share": float(((trend_regime == "range") & (volatility_regime == "low_vol")).mean()),
        "low_liquidity_share": float((liquidity_regime == "low_liquidity").mean()),
        "favorable_breakout_regime_share": float((((trend_regime == "bullish_trend") | (trend_regime == "bearish_trend")) & (liquidity_regime != "low_liquidity")).mean()),
        "favorable_reversion_regime_share": float(((trend_regime == "range") & (liquidity_regime != "low_liquidity")).mean()),
    }

    return {
        "regime_map": [
            {
                "timestamp": idx.isoformat(),
                "trend_regime": str(frame.at[idx, "trend_regime"]),
                "volatility_regime": str(frame.at[idx, "volatility_regime"]),
                "liquidity_regime": str(frame.at[idx, "liquidity_regime"]),
                "combined_regime": str(frame.at[idx, "combined_regime"]),
            }
            for idx in frame.index
        ],
        "regime_share": {
            "trend": _share_map(trend_regime),
            "volatility": _share_map(volatility_regime),
            "liquidity": _share_map(liquidity_regime),
            "combined": _share_map(combined),
        },
        "average_duration": {
            "trend": _average_run_lengths(trend_regime),
            "volatility": _average_run_lengths(volatility_regime),
            "liquidity": _average_run_lengths(liquidity_regime),
            "combined": _average_run_lengths(combined),
        },
        "transition_matrix": {
            "trend": _transition_matrix(trend_regime),
            "volatility": _transition_matrix(volatility_regime),
            "liquidity": _transition_matrix(liquidity_regime),
            "combined": _transition_matrix(combined),
        },
        "metrics_by_regime": {
            "trend": _top_regime_metrics(frame, group_col="trend_regime", return_col="returns", range_col="range_pips", spread_col="spread", volume_col="volume"),
            "volatility": _top_regime_metrics(frame, group_col="volatility_regime", return_col="returns", range_col="range_pips", spread_col="spread", volume_col="volume"),
            "liquidity": _top_regime_metrics(frame, group_col="liquidity_regime", return_col="returns", range_col="range_pips", spread_col="spread", volume_col="volume"),
            "combined": _top_regime_metrics(frame, group_col="combined_regime", return_col="returns", range_col="range_pips", spread_col="spread", volume_col="volume"),
        },
        "score_inputs": regime_score_inputs,
    }


def _confidence_adjustment_factor(label: str | None, *, high: float, medium: float) -> float:
    if label == "HIGH":
        return high
    if label == "MEDIUM":
        return medium
    if label in {"LOW", "INSUFFICIENT_DATA"}:
        return -medium
    return 0.0


def build_market_structure_profile(
    prepared: PreparedDataset,
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    number_of_bars: Optional[int] = None,
    config: Optional[MarketStructureConfig] = None,
    tp_config: Optional[TrendPersistenceConfig] = None,
) -> MarketStructureProfile:
    """Build a reproducible directional structure profile from a prepared dataset."""
    cfg = config or MarketStructureConfig()
    profile_meta = resolve_market_structure_profile(symbol, timeframe)
    profile_overrides = (
        resolve_market_structure_profile_overrides(symbol, timeframe)
        if cfg.apply_profile_overrides
        else {}
    )
    if profile_overrides:
        cfg = replace(cfg, **profile_overrides)
    schema = prepared.schema
    data = prepared.data
    points = _detect_swings(
        data,
        symbol=symbol,
        cfg=cfg,
        high_col=schema.high,
        low_col=schema.low,
        close_col=schema.close,
    )
    chains = _build_directional_chains(points)
    legs = _build_legs(data, symbol=symbol, points=points, close_col=schema.close)

    tp_result = run_eds_trend_persistence(
        data[[schema.open, schema.high, schema.low, schema.close, schema.volume, schema.spread]].copy(),
        symbol=symbol,
        timeframe=timeframe,
        cfg=tp_config or TrendPersistenceConfig(),
        boot=BootstrapConfig(n_boot=cfg.eds_boot_n),
        perm=PermutationConfig(n_perm=cfg.eds_perm_n),
        close_col=schema.close,
        high_col=schema.high,
        low_col=schema.low,
    )
    eds_expectancy = _safe_float(tp_result.stats.expectancy_r)
    eds_confirmed = bool(tp_result.stats.edge_confirmed)
    mr_result = run_eds_mean_reversion(
        data[[schema.open, schema.high, schema.low, schema.close, schema.volume, schema.spread]].copy(),
        symbol=symbol,
        timeframe=timeframe,
        cfg=MeanReversionConfig(),
        boot=BootstrapConfig(n_boot=cfg.eds_boot_n),
        perm=PermutationConfig(n_perm=cfg.eds_perm_n),
        close_col=schema.close,
        high_col=schema.high,
        low_col=schema.low,
    )
    mr_expectancy = _safe_float(mr_result.stats.expectancy_r)
    mr_confirmed = bool(mr_result.stats.edge_confirmed)
    range_metrics = _compute_range_reversion_metrics(
        data,
        symbol=symbol,
        close_col=schema.close,
        high_col=schema.high,
        low_col=schema.low,
        range_window=cfg.range_window,
        breakout_horizon=cfg.breakout_horizon,
    )
    distribution_metrics = _compute_distribution_metrics(
        data,
        symbol=symbol,
        close_col=schema.close,
        high_col=schema.high,
        low_col=schema.low,
    )
    excursion_studies = _compute_excursion_studies(
        data,
        symbol=symbol,
        points=points,
        legs=legs,
        close_col=schema.close,
        high_col=schema.high,
        low_col=schema.low,
        horizon=cfg.breakout_horizon,
    )
    regime_engine = _compute_regime_engine(
        data,
        symbol=symbol,
        close_col=schema.close,
        high_col=schema.high,
        low_col=schema.low,
        volume_col=schema.volume,
        spread_col=schema.spread,
        cfg=cfg,
    )
    phase6_commentary = {
        "distribution_risk": distribution_metrics.get("normality", {}).get("label", "INSUFFICIENT_DATA"),
        "breakout_quality": _phase6_breakout_quality(
            range_metrics["breakout_follow_probability"],
            range_metrics["false_break_frequency"],
            range_metrics["retest_success_rate"],
        ),
        "retracement_profile": _phase6_retracement_label(
            range_metrics.get("retracement_depth_distribution", {}).get("p50"),
            range_metrics.get("extension_behavior", {}).get("p75_extension_pips"),
        ),
        "breakout_excursion_fit": _phase6_excursion_label(excursion_studies.get("breakout", {})),
        "pullback_excursion_fit": _phase6_excursion_label(excursion_studies.get("pullback_resumption", {})),
    }

    score_rows = _build_score_rows(
        points=points,
        chains=chains,
        legs=legs,
        range_metrics=range_metrics,
        mr_expectancy=mr_expectancy,
        mr_confirmed=mr_confirmed,
        eds_expectancy=eds_expectancy,
        eds_confirmed=eds_confirmed,
    )
    score_map = _score_map(score_rows)
    direction_score = _weighted_group_score(score_rows, "direction", clip=100.0)
    trend_confidence_score = max(
        0.0,
        min(100.0, _weighted_group_score(score_rows, "confidence")),
    )
    reversion_score = max(
        0.0,
        min(100.0, _weighted_group_score(score_rows, "reversion")),
    )
    chop_score = max(
        0.0,
        min(100.0, _weighted_group_score(score_rows, "chop")),
    )
    reversion_confidence_score = max(
        0.0,
        min(
            100.0,
            (score_map.get("sample_quality", 0.0) * 0.35)
            + (score_map.get("range_state_detection", 0.0) * 0.25)
            + (score_map.get("false_break_reentry", 0.0) * 0.20)
            + (score_map.get("mean_reversion_metrics", 0.0) * 0.20),
        ),
    )
    quality_adjustment: Dict[str, Any] = {
        "model_version": cfg.model_version,
        "baseline_id": cfg.baseline_id,
        "profile_overrides": profile_overrides,
        "stability": None,
        "robustness": None,
        "trend_confidence_delta": 0.0,
        "reversion_confidence_delta": 0.0,
    }
    if cfg.apply_quality_adjustments:
        from services.research.market_structure_robustness import build_market_structure_robustness_report
        from services.research.market_structure_stability import build_market_structure_stability_report

        nested_cfg = replace(cfg, apply_quality_adjustments=False)
        stability = build_market_structure_stability_report(
            prepared,
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source,
            range_by=range_by,
            start_date=start_date,
            end_date=end_date,
            number_of_bars=number_of_bars,
            config=nested_cfg,
        )
        robustness = build_market_structure_robustness_report(
            prepared,
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source,
            range_by=range_by,
            start_date=start_date,
            end_date=end_date,
            number_of_bars=number_of_bars,
            config=nested_cfg,
        )
        trend_delta = _confidence_adjustment_factor(
            stability.get("stability"),
            high=cfg.stability_confidence_weight * 100.0,
            medium=cfg.stability_confidence_weight * 50.0,
        ) + _confidence_adjustment_factor(
            robustness.get("robustness"),
            high=cfg.robustness_confidence_weight * 100.0,
            medium=cfg.robustness_confidence_weight * 50.0,
        )
        reversion_delta = _confidence_adjustment_factor(
            stability.get("stability"),
            high=cfg.stability_confidence_weight * 70.0,
            medium=cfg.stability_confidence_weight * 35.0,
        ) + _confidence_adjustment_factor(
            robustness.get("robustness"),
            high=cfg.robustness_confidence_weight * 40.0,
            medium=cfg.robustness_confidence_weight * 20.0,
        )
        trend_confidence_score = max(0.0, min(100.0, trend_confidence_score + trend_delta))
        reversion_confidence_score = max(0.0, min(100.0, reversion_confidence_score + reversion_delta))
        quality_adjustment = {
            "model_version": cfg.model_version,
            "baseline_id": cfg.baseline_id,
            "profile_overrides": profile_overrides,
            "stability": {
                "label": stability.get("stability"),
                "agreement_rate": stability.get("agreement_rate"),
                "confidence_drift": stability.get("confidence_drift"),
                "regime_state": "TRANSITIONAL" if stability.get("stability") == "LOW" else "STABLE",
            },
            "robustness": {
                "label": robustness.get("robustness"),
                "verdict_agreement_rate": robustness.get("verdict_agreement_rate"),
            },
            "trend_confidence_delta": trend_delta,
            "reversion_confidence_delta": reversion_delta,
        }
    trend_bias_score = abs(direction_score) * (trend_confidence_score / 100.0)
    total_nontrend_weight = cfg.reversion_score_weight + cfg.chop_score_weight
    reversion_mix = (
        (reversion_score * cfg.reversion_score_weight) + (chop_score * cfg.chop_score_weight)
    ) / total_nontrend_weight if total_nontrend_weight > 0 else 0.0
    reversion_bias_score = min(
        100.0,
        reversion_mix * (reversion_confidence_score / 100.0),
    )
    final_score = _clip_score(trend_bias_score - reversion_bias_score)
    decision_confidence_score = (
        trend_confidence_score
        if trend_bias_score >= reversion_bias_score
        else reversion_confidence_score
    )
    verdict = _final_verdict(
        trend_bias_score,
        reversion_bias_score,
        trend_confidence_score,
        reversion_confidence_score,
        bias_verdict_min_gap=cfg.bias_verdict_min_gap,
        trend_confidence_min=cfg.trend_confidence_min,
        reversion_confidence_min=cfg.reversion_confidence_min,
    )

    bullish_labels = sum(1 for point in points if point.label in ("HH", "HL"))
    bearish_labels = sum(1 for point in points if point.label in ("LL", "LH"))
    pullback_legs = [leg for leg in legs if leg.pullback_depth is not None]
    continuation_rate = float(
        np.mean([1.0 if leg.continuation_after_pullback else 0.0 for leg in pullback_legs])
    ) if pullback_legs else 0.0

    values = [
        _metric("swing_points_total", len(points)),
        _metric("bullish_label_count", bullish_labels),
        _metric("bearish_label_count", bearish_labels),
        _metric("chain_count", len(chains)),
        _metric("trend_leg_count", len(legs)),
        _metric("pullback_leg_count", len(pullback_legs)),
        _metric("continuation_after_pullback_rate", continuation_rate),
        _metric("direction_score", direction_score),
        _metric("trend_confidence_score", trend_confidence_score),
        _metric("reversion_score", reversion_score),
        _metric("reversion_confidence_score", reversion_confidence_score),
        _metric("decision_confidence_score", decision_confidence_score),
        _metric("trend_bias_score", trend_bias_score),
        _metric("reversion_bias_score", reversion_bias_score),
        _metric("chop_score", chop_score),
        _metric("final_score", final_score),
        _metric("verdict", verdict),
        _metric("eds1_expectancy_r", mr_expectancy),
        _metric("eds1_confirmed", 1 if mr_confirmed else 0),
        _metric("eds2_expectancy_r", eds_expectancy),
        _metric("eds2_confirmed", 1 if eds_confirmed else 0),
    ]
    for key, value in range_metrics.items():
        values.append(_metric(key, value))
    for key, value in distribution_metrics.get("tail_metrics", {}).items():
        values.append(_metric(f"distribution_{key}", value))
    for key, value in distribution_metrics.get("normality", {}).items():
        values.append(_metric(f"normality_{key}", value))
    for key, value in distribution_metrics.get("asymmetry", {}).items():
        values.append(_metric(f"distribution_asymmetry_{key}", value))
    for event_type, study in excursion_studies.items():
        values.append(_metric(f"{event_type}_event_count", study.get("count")))
        values.append(_metric(f"{event_type}_avg_mfe_pips", study.get("avg_mfe_pips")))
        values.append(_metric(f"{event_type}_avg_mae_pips", study.get("avg_mae_pips")))
        values.append(_metric(f"{event_type}_time_to_mfe_bars", study.get("time_to_mfe_bars")))
        values.append(_metric(f"{event_type}_time_to_mae_bars", study.get("time_to_mae_bars")))
    for axis, share_map in regime_engine.get("regime_share", {}).items():
        for label, value in share_map.items():
            values.append(_metric(f"regime_share_{axis}_{label}", value))
    for key, value in regime_engine.get("score_inputs", {}).items():
        values.append(_metric(f"regime_score_input_{key}", value))
    for row in score_rows:
        values.append(_metric(f"score_{row.key}", row.score, label=row.label))
        values.append(_metric(f"contribution_{row.key}", row.contribution, label=row.label))

    stability_meta = quality_adjustment.get("stability") or {}
    summary = {
        "direction_score": direction_score,
        "trend_confidence_score": trend_confidence_score,
        "reversion_score": reversion_score,
        "reversion_confidence_score": reversion_confidence_score,
        "decision_confidence_score": decision_confidence_score,
        "trend_bias_score": trend_bias_score,
        "reversion_bias_score": reversion_bias_score,
        "chop_score": chop_score,
        "final_score": final_score,
        "verdict": verdict,
        "regime_state": "TRANSITIONAL" if stability_meta.get("label") == "LOW" else "STABLE",
        "direction": "bullish" if direction_score > 0 else "bearish" if direction_score < 0 else "neutral",
        "score_row_count": len(score_rows),
        "swing_count": len(points),
        "chain_count": len(chains),
        "trend_leg_count": len(legs),
        "pullback_leg_count": len(pullback_legs),
        "continuation_after_pullback_rate": continuation_rate,
        "range_duration_bars": range_metrics["range_duration_bars"],
        "range_height_pips": range_metrics["range_height_pips"],
        "breakout_follow_probability": range_metrics["breakout_follow_probability"],
        "false_break_frequency": range_metrics["false_break_frequency"],
        "reentry_probability": range_metrics["reentry_probability"],
        "half_life_bars": range_metrics["half_life_bars"],
        "zscore_reentry_rate": range_metrics["zscore_reentry_rate"],
        "band_reentry_rate": range_metrics["band_reentry_rate"],
        "choppiness_index": range_metrics["choppiness_index"],
        "whipsaw_rate": range_metrics["whipsaw_rate"],
        "false_break_reversal_size_pips": range_metrics["false_break_reversal_size_pips"],
        "retest_success_rate": range_metrics["retest_success_rate"],
        "eds2_expectancy_r": eds_expectancy,
        "eds2_confirmed": eds_confirmed,
        "eds1_expectancy_r": mr_expectancy,
        "eds1_confirmed": mr_confirmed,
        "is_valid": prepared.report.is_valid,
        "model_version": cfg.model_version,
        "baseline_id": cfg.baseline_id,
        "distribution": distribution_metrics,
        "breakout_analysis": {
            "follow_through_probability": range_metrics["breakout_follow_probability"],
            "failure_rate": range_metrics["false_break_frequency"],
            "false_break_reversal_size_pips": range_metrics["false_break_reversal_size_pips"],
            "retest_success_rate": range_metrics["retest_success_rate"],
            "retracement_depth_distribution": range_metrics["retracement_depth_distribution"],
            "extension_behavior": range_metrics["extension_behavior"],
        },
        "excursions": excursion_studies,
        "phase6_commentary": phase6_commentary,
        "regime_map": regime_engine["regime_map"],
        "regime_share": regime_engine["regime_share"],
        "regime_durations": regime_engine["average_duration"],
        "regime_transition_matrix": regime_engine["transition_matrix"],
        "regime_conditioned_metrics": regime_engine["metrics_by_regime"],
        "regime_score_inputs": regime_engine["score_inputs"],
        **profile_meta,
        "calibration_metadata": quality_adjustment,
    }
    summary["strategy_fit"] = build_strategy_fit(summary)

    return MarketStructureProfile(
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=start_date,
        end_date=end_date,
        number_of_bars=number_of_bars,
        bar_count=len(data),
        report=prepared.report,
        values=values,
        score_rows=score_rows,
        swing_points=points,
        trend_legs=legs,
        summary=summary,
    )


def build_market_structure_research_profile(
    prepared: PreparedDataset,
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    number_of_bars: Optional[int] = None,
    config: Optional[MarketStructureConfig] = None,
    tp_config: Optional[TrendPersistenceConfig] = None,
) -> MarketStructureProfile:
    """Build Market Structure with expensive quality-adjusted research layers enabled."""
    base_cfg = config or MarketStructureConfig()
    research_cfg = replace(
        base_cfg,
        apply_quality_adjustments=True,
        eds_boot_n=base_cfg.research_eds_boot_n,
        eds_perm_n=base_cfg.research_eds_perm_n,
    )
    return build_market_structure_profile(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=start_date,
        end_date=end_date,
        number_of_bars=number_of_bars,
        config=research_cfg,
        tp_config=tp_config,
    )

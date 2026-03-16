"""Core Metric MVP service for Edge Lab."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from apps.edge.data.models import DataQualityReportModel, PreparedDataset

from .base import MetricCalculator, MetricContext, MetricValue
from .registry import MetricRegistry


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _to_metric(family: str, key: str, value: Any, **context: Any) -> MetricValue:
    number = _safe_float(value)
    if number is not None:
        return MetricValue(family=family, key=key, value=number, context=context)
    return MetricValue(
        family=family,
        key=key,
        value=str(value) if value is not None else None,
        value_type="text",
        context=context,
    )


def _periods_per_year(timeframe: str) -> float:
    mapping = {
        "M1": 60.0 * 24.0 * 252.0,
        "M5": 12.0 * 24.0 * 252.0,
        "M15": 4.0 * 24.0 * 252.0,
        "M30": 2.0 * 24.0 * 252.0,
        "H1": 24.0 * 252.0,
        "H4": 6.0 * 252.0,
        "D1": 252.0,
        "W1": 52.0,
    }
    return mapping.get(timeframe.upper(), 252.0)


def _pip_size(symbol: str) -> float:
    upper = symbol.upper()
    if upper.endswith("JPY"):
        return 0.01
    return 0.0001


def _returns(close: pd.Series) -> pd.Series:
    return close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def _log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()


def _roc(close: pd.Series, periods: int) -> pd.Series:
    return close.pct_change(periods=periods).replace([np.inf, -np.inf], np.nan).dropna()


def _rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    return returns.rolling(window).std().dropna()


def _point_columns(data: pd.DataFrame, symbol: str) -> Dict[str, pd.Series]:
    pip = _pip_size(symbol)
    point = pip / 10.0
    body = (data["Close"] - data["Open"]).abs() / pip
    total_range = (data["High"] - data["Low"]).abs() / pip
    upper = (data["High"] - data[["Open", "Close"]].max(axis=1)).clip(lower=0) / pip
    lower = (data[["Open", "Close"]].min(axis=1) - data["Low"]).clip(lower=0) / pip
    spread_pips = data["Spread"] * point / pip
    return {
        "pip_size": pd.Series([pip]),
        "point_size": pd.Series([point]),
        "body_pips": body,
        "range_pips": total_range,
        "upper_wick_pips": upper,
        "lower_wick_pips": lower,
        "spread_pips": spread_pips,
    }


@dataclass(frozen=True)
class CoreMetricProfile:
    """Persistable Core Metric run payload."""

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
        }


class ReturnsCalculator:
    family = "returns"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        close = context.data[context.schema.close]
        returns = _returns(close)
        log_returns = _log_returns(close)
        periods = _periods_per_year(context.timeframe)
        values = [
            _to_metric(self.family, "mean", returns.mean()),
            _to_metric(self.family, "median", returns.median()),
            _to_metric(self.family, "std", returns.std()),
            _to_metric(self.family, "positive_rate", (returns > 0).mean()),
            _to_metric(self.family, "log_mean", log_returns.mean()),
            _to_metric(self.family, "total_return", close.iloc[-1] / close.iloc[0] - 1.0),
            _to_metric(self.family, "annualized_return", returns.mean() * periods),
        ]
        return values


class RocCalculator:
    family = "roc"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        close = context.data[context.schema.close]
        values: List[MetricValue] = []
        for periods in (1, 5, 10):
            roc = _roc(close, periods)
            label = f"roc_{periods}"
            values.extend(
                [
                    _to_metric(self.family, f"{label}_mean", roc.mean(), periods=periods),
                    _to_metric(self.family, f"{label}_median", roc.median(), periods=periods),
                    _to_metric(
                        self.family,
                        f"{label}_abs_p95",
                        roc.abs().quantile(0.95),
                        periods=periods,
                    ),
                ]
            )
        return values


class CandlesCalculator:
    family = "candles"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        point_data = _point_columns(context.data, context.symbol)
        open_col = context.data[context.schema.open]
        close_col = context.data[context.schema.close]
        range_pips = point_data["range_pips"]
        body_pips = point_data["body_pips"]
        upper_wick = point_data["upper_wick_pips"]
        lower_wick = point_data["lower_wick_pips"]
        values = [
            _to_metric(self.family, "body_pips_mean", body_pips.mean()),
            _to_metric(self.family, "range_pips_mean", range_pips.mean()),
            _to_metric(self.family, "upper_wick_pips_mean", upper_wick.mean()),
            _to_metric(self.family, "lower_wick_pips_mean", lower_wick.mean()),
            _to_metric(
                self.family,
                "body_to_range_mean",
                (body_pips / range_pips.replace(0, np.nan)).mean(),
            ),
            _to_metric(self.family, "bullish_rate", (close_col > open_col).mean()),
            _to_metric(self.family, "bearish_rate", (close_col < open_col).mean()),
            _to_metric(
                self.family,
                "doji_rate",
                (body_pips <= 0.1 * range_pips.replace(0, np.nan)).fillna(False).mean(),
            ),
        ]
        return values


class RangesCalculator:
    family = "ranges"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        point_data = _point_columns(context.data, context.symbol)
        range_pips = point_data["range_pips"]
        oc_pips = (context.data["Close"] - context.data["Open"]).abs() / _pip_size(
            context.symbol
        )
        median_range = range_pips.median()
        values = [
            _to_metric(self.family, "hl_mean_pips", range_pips.mean()),
            _to_metric(self.family, "hl_median_pips", range_pips.median()),
            _to_metric(self.family, "hl_p95_pips", range_pips.quantile(0.95)),
            _to_metric(self.family, "oc_mean_pips", oc_pips.mean()),
            _to_metric(self.family, "expansion_rate", (range_pips > median_range).mean()),
        ]
        return values


class VolatilityCalculator:
    family = "volatility"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        returns = _returns(context.data[context.schema.close])
        rolling = _rolling_volatility(returns)
        annual_factor = math.sqrt(_periods_per_year(context.timeframe))
        range_pips = _point_columns(context.data, context.symbol)["range_pips"]
        values = [
            _to_metric(self.family, "return_std", returns.std()),
            _to_metric(self.family, "annualized_return_std", returns.std() * annual_factor),
            _to_metric(self.family, "rolling_20_std_mean", rolling.mean()),
            _to_metric(self.family, "rolling_20_std_p95", rolling.quantile(0.95)),
            _to_metric(self.family, "range_std_pips", range_pips.std()),
        ]
        return values


class SpreadCalculator:
    family = "spread"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        point_data = _point_columns(context.data, context.symbol)
        spread_pips = point_data["spread_pips"]
        range_pips = point_data["range_pips"]
        values = [
            _to_metric(self.family, "mean_pips", spread_pips.mean()),
            _to_metric(self.family, "median_pips", spread_pips.median()),
            _to_metric(self.family, "p95_pips", spread_pips.quantile(0.95)),
            _to_metric(
                self.family,
                "spread_to_range_mean",
                (spread_pips / range_pips.replace(0, np.nan)).mean(),
            ),
            _to_metric(self.family, "zero_spread_rate", (spread_pips <= 0).mean()),
        ]
        return values


class VolumeActivityCalculator:
    family = "volume_activity"

    def compute(self, context: MetricContext) -> List[MetricValue]:
        volume = context.data[context.schema.volume]
        active_hours = context.data.index.hour.nunique() if len(context.data.index) else 0
        values = [
            _to_metric(self.family, "mean", volume.mean()),
            _to_metric(self.family, "median", volume.median()),
            _to_metric(self.family, "p95", volume.quantile(0.95)),
            _to_metric(self.family, "zero_rate", (volume <= 0).mean()),
            _to_metric(self.family, "active_hours", active_hours),
            _to_metric(self.family, "bars", len(volume)),
        ]
        return values


DEFAULT_CALCULATORS: List[MetricCalculator] = [
    ReturnsCalculator(),
    RocCalculator(),
    CandlesCalculator(),
    RangesCalculator(),
    VolatilityCalculator(),
    SpreadCalculator(),
    VolumeActivityCalculator(),
]


def build_default_registry() -> MetricRegistry:
    return MetricRegistry.from_calculators(DEFAULT_CALCULATORS)


def build_core_metric_profile(
    prepared: PreparedDataset,
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    number_of_bars: Optional[int] = None,
    registry: Optional[MetricRegistry] = None,
) -> CoreMetricProfile:
    """Build a normalized Core Metric profile from a prepared dataset."""
    registry = registry or build_default_registry()
    context = MetricContext(
        symbol=symbol,
        timeframe=timeframe,
        data=prepared.data,
        schema=prepared.schema,
        report=prepared.report,
    )
    values: List[MetricValue] = [
        _to_metric("dataset", "warning_count", len(prepared.report.warnings)),
        _to_metric("dataset", "fatal_error_count", len(prepared.report.fatal_errors)),
        _to_metric("dataset", "is_valid", 1 if prepared.report.is_valid else 0),
        _to_metric("dataset", "row_count", len(prepared.data)),
        _to_metric("dataset", "pip_size", _pip_size(symbol)),
    ]
    for calculator in registry.all():
        values.extend(calculator.compute(context))

    summary = {
        "family_count": len(registry.families()),
        "metric_count": len(values),
        "warning_count": len(prepared.report.warnings),
        "fatal_error_count": len(prepared.report.fatal_errors),
        "is_valid": prepared.report.is_valid,
    }
    return CoreMetricProfile(
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=start_date,
        end_date=end_date,
        number_of_bars=number_of_bars,
        bar_count=len(prepared.data),
        report=prepared.report,
        values=values,
        summary=summary,
    )

"""Cleaning policies for analysis-ready OHLCVS datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from backend.common.datetime_utils import normalize_timezone_for_series
from backend.services.market_data.data_manipulator import TimeframeManager

from .models import CanonicalOHLCVSSchema, CleaningAction, DataQualityReportModel


@dataclass(frozen=True)
class CleaningConfig:
    """Cleaning policies for OHLCVS preparation."""

    timeframe: Optional[str] = None
    missing_bar_policy: str = "leave"
    broker_timezone: str = "UTC"
    output_timezone: str = "UTC"
    make_timezone_naive: bool = True
    drop_weekends: bool = True
    holiday_dates: Iterable[str] = field(default_factory=tuple)
    spread_anomaly_action: str = "clip"
    spread_zscore_threshold: float = 4.0


def _expected_frequency(config: CleaningConfig) -> Optional[str]:
    if not config.timeframe:
        return None
    return TimeframeManager.timeframe_to_frequency(config.timeframe)


def _normalize_timezone(df: pd.DataFrame, config: CleaningConfig) -> pd.DataFrame:
    out = df.copy()
    idx = out.index
    if idx.tz is None:
        idx = idx.tz_localize(config.broker_timezone)
    out.index = normalize_timezone_for_series(
        idx,
        target_tz=config.output_timezone,
        make_naive=config.make_timezone_naive,
    )
    return out.sort_index()


def _handle_missing_bars(
    df: pd.DataFrame,
    schema: CanonicalOHLCVSSchema,
    config: CleaningConfig,
    report: DataQualityReportModel,
) -> pd.DataFrame:
    if config.missing_bar_policy == "leave":
        return df

    expected_freq = _expected_frequency(config)
    if not expected_freq or len(df) < 2:
        return df

    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq=expected_freq)
    missing_index = full_index.difference(df.index)
    if len(missing_index) == 0:
        return df

    out = df.reindex(full_index)
    if config.missing_bar_policy == "ffill_close":
        prev_close = out[schema.close].ffill()
        for col in schema.price_columns:
            out[col] = out[col].fillna(prev_close)
        if schema.volume in out.columns:
            out[schema.volume] = out[schema.volume].fillna(0.0)
        if schema.spread in out.columns:
            out[schema.spread] = out[schema.spread].ffill().fillna(0.0)

    report.add_action(
        CleaningAction(
            action="missing_bar_policy",
            count=len(missing_index),
            details={"policy": config.missing_bar_policy},
        )
    )
    return out


def _drop_weekends_and_holidays(
    df: pd.DataFrame,
    config: CleaningConfig,
    report: DataQualityReportModel,
) -> pd.DataFrame:
    out = df
    if config.drop_weekends:
        weekend_mask = out.index.dayofweek >= 5
        weekend_count = int(weekend_mask.sum())
        if weekend_count and weekend_count < len(out):
            out = out.loc[~weekend_mask]
            report.add_action(
                CleaningAction("drop_weekends", count=weekend_count)
            )

    holiday_dates = tuple(config.holiday_dates)
    if holiday_dates:
        holiday_set = {pd.Timestamp(d).date() for d in holiday_dates}
        holiday_mask = out.index.normalize().date
        keep_mask = np.array([d not in holiday_set for d in holiday_mask], dtype=bool)
        removed = int((~keep_mask).sum())
        if removed and removed < len(out):
            out = out.loc[keep_mask]
            report.add_action(
                CleaningAction("drop_holidays", count=removed)
            )

    return out


def _handle_spread_anomalies(
    df: pd.DataFrame,
    schema: CanonicalOHLCVSSchema,
    config: CleaningConfig,
    report: DataQualityReportModel,
) -> pd.DataFrame:
    if schema.spread not in df.columns or config.spread_anomaly_action == "keep":
        return df

    out = df.copy()
    spread = pd.to_numeric(out[schema.spread], errors="coerce").astype(float)
    out[schema.spread] = spread
    valid = spread.dropna()
    if len(valid) < 3 or valid.std() == 0:
        return out

    z = (spread - valid.mean()) / valid.std()
    anomaly_mask = z.abs() > config.spread_zscore_threshold
    count = int(anomaly_mask.fillna(False).sum())
    if count == 0:
        return out

    if config.spread_anomaly_action == "clip":
        upper = float(valid.mean() + config.spread_zscore_threshold * valid.std())
        lower = max(0.0, float(valid.mean() - config.spread_zscore_threshold * valid.std()))
        out.loc[anomaly_mask, schema.spread] = spread.clip(lower=lower, upper=upper)[anomaly_mask]
    elif config.spread_anomaly_action == "drop":
        out = out.loc[~anomaly_mask.fillna(False)]

    report.add_action(
        CleaningAction(
            action="spread_anomaly_handling",
            count=count,
            details={"policy": config.spread_anomaly_action},
        )
    )
    return out


def clean_dataset(
    df: pd.DataFrame,
    *,
    report: DataQualityReportModel,
    schema: CanonicalOHLCVSSchema | None = None,
    config: CleaningConfig | None = None,
) -> pd.DataFrame:
    """Normalize timezone, handle missing bars, weekends/holidays, and spread anomalies."""
    schema = schema or CanonicalOHLCVSSchema()
    config = config or CleaningConfig()

    out = _normalize_timezone(df, config)
    report.add_check("timezone_normalization")

    out = _handle_missing_bars(out, schema, config, report)
    report.add_check("missing_bar_policy")

    out = _drop_weekends_and_holidays(out, config, report)
    report.add_check("calendar_filters")

    out = _handle_spread_anomalies(out, schema, config, report)
    report.add_check("spread_cleaning")

    return out

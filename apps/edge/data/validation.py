"""Validation helpers for analysis-ready OHLCVS datasets."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from apps.utils.data_manipulator import TimeframeManager
from apps.utils.data_validator import DataValidator

from .models import CanonicalOHLCVSSchema, DataQualityReportModel, DatasetIssue


def _add_issue(
    report: DataQualityReportModel,
    *,
    code: str,
    severity: str,
    message: str,
    count: int = 0,
    **details,
) -> None:
    report.add_issue(
        DatasetIssue(
            code=code,
            severity=severity,
            message=message,
            count=count,
            details=details,
        )
    )


def _expected_frequency(timeframe: Optional[str]) -> Optional[str]:
    if not timeframe:
        return None
    return TimeframeManager.timeframe_to_frequency(timeframe)


def validate_dataset(
    df: pd.DataFrame,
    *,
    schema: CanonicalOHLCVSSchema | None = None,
    timeframe: Optional[str] = None,
) -> DataQualityReportModel:
    """Validate schema, continuity, OHLC logic, duplicates, spread, and volume."""
    schema = schema or CanonicalOHLCVSSchema()
    report = DataQualityReportModel()
    validator = DataValidator()

    report.add_check("schema")
    if not isinstance(df.index, pd.DatetimeIndex):
        _add_issue(
            report,
            code="missing_datetime_index",
            severity="fatal",
            message="Dataset must use a DatetimeIndex before analysis.",
        )
        return report

    for col in schema.price_columns:
        if col not in df.columns:
            _add_issue(
                report,
                code=f"missing_{col.lower()}",
                severity="fatal",
                message=f"Required price column '{col}' is missing.",
            )

    for col in (schema.volume, schema.spread):
        if col not in df.columns:
            _add_issue(
                report,
                code=f"missing_{col.lower()}",
                severity="warning",
                message=f"Optional input column '{col}' is missing and will be synthesized.",
            )

    report.add_check("ohlc_logic")
    all_valid, _, issues = validator.validate_price_sanity(df, mark_invalid=False)
    if not all_valid:
        invalid_count = int(
            sum(int(issue.get("count", 0)) for issue in issues if issue.get("type") == "price_sanity")
        )
        _add_issue(
            report,
            code="invalid_ohlc",
            severity="fatal",
            message="OHLC logical relationships are invalid.",
            count=invalid_count,
        )

    report.add_check("timestamp_continuity")
    expected_freq = _expected_frequency(timeframe)
    _, gaps = validator.detect_gaps(df, expected_frequency=expected_freq)
    if gaps:
        total_missing = int(sum(max(0, int(g["expected_periods"]) - 1) for g in gaps))
        _add_issue(
            report,
            code="time_gaps_detected",
            severity="warning",
            message="Timestamp gaps were detected in the dataset.",
            count=len(gaps),
            missing_bars=total_missing,
        )

    missing_df, missing_info = validator.check_missing_timestamps(
        df,
        expected_frequency=expected_freq,
    )
    if missing_info:
        info = missing_info[0]
        _add_issue(
            report,
            code="missing_timestamps",
            severity="warning",
            message="Expected timestamps are missing from the dataset.",
            count=int(info.get("count", len(missing_df))),
            coverage=float(info.get("coverage", np.nan)),
        )

    report.add_check("duplicates")
    duplicates_df, duplicate_issues = validator.detect_duplicates(df)
    if duplicate_issues:
        issue = duplicate_issues[0]
        _add_issue(
            report,
            code="duplicate_timestamps",
            severity="fatal",
            message="Duplicate timestamps were found.",
            count=int(issue.get("count", len(duplicates_df))),
        )

    report.add_check("spread")
    spread_stats, spread_issues = validator.analyze_spread(df)
    report.metadata["spread_stats"] = spread_stats
    for issue in spread_issues:
        _add_issue(
            report,
            code="spread_warning",
            severity="warning",
            message="Spread anomalies were detected.",
            count=int(issue.get("count", 0)),
            **{k: v for k, v in issue.items() if k not in {"type", "count"}},
        )

    report.add_check("volume")
    zero_volume_df, zero_volume_issues = validator.detect_zero_volume(df)
    if zero_volume_issues:
        _add_issue(
            report,
            code="zero_volume",
            severity="warning",
            message="Zero-volume bars were detected.",
            count=len(zero_volume_df),
        )

    return report

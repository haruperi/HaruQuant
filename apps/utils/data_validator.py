"""
DataValidator - Market Data Quality Validation.

This module provides comprehensive validation functionality for market data quality,
including price sanity checks, gap detection, spike detection, missing timestamps,
and validation reporting.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
import pandas as pd

from apps.utils.logger import logger
from apps.utils.path_utils import ensure_parent_dir


@dataclass
class DataQualityReport:
    """Comprehensive data quality report.

    This dataclass contains all validation results in a structured format,
    including quality score, issues found, and detailed metrics.
    """

    timestamp: datetime
    total_rows: int
    checks_performed: List[str]
    issues_found: List[Dict[str, Any]]
    summary: Dict[str, Any]
    quality_score: float
    is_valid: bool

    # Detailed metrics
    price_sanity_valid: bool = True
    gaps_count: int = 0
    anomalies_count: int = 0
    missing_timestamps_count: int = 0
    zero_volume_count: int = 0
    duplicates_count: int = 0
    spread_stats: Optional[Dict[str, float]] = None

    def __str__(self) -> str:
        """Return string representation of the report."""
        return (
            f"DataQualityReport(quality_score={self.quality_score:.1f}%, "
            f"issues={len(self.issues_found)}, valid={self.is_valid})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "total_rows": self.total_rows,
            "checks_performed": self.checks_performed,
            "issues_found": self.issues_found,
            "summary": self.summary,
            "quality_score": self.quality_score,
            "is_valid": self.is_valid,
            "price_sanity_valid": self.price_sanity_valid,
            "gaps_count": self.gaps_count,
            "anomalies_count": self.anomalies_count,
            "missing_timestamps_count": self.missing_timestamps_count,
            "zero_volume_count": self.zero_volume_count,
            "duplicates_count": self.duplicates_count,
            "spread_stats": self.spread_stats,
        }


class DataValidator:
    """
    Market data quality validation class.

    Provides comprehensive validation methods for:
    - Price sanity checks (OHLC relationships)
    - Gap detection in time series
    - Spike detection and anomaly marking
    - Missing timestamps checker
    - Validation reporting
    """

    def __init__(self, z_score_threshold: float = 3.0, iqr_multiplier: float = 1.5):
        """
        Initialize DataValidator instance.

        Args:
            z_score_threshold: Z-score threshold for spike detection (default: 3.0)
            iqr_multiplier: IQR multiplier for outlier detection (default: 1.5)
        """
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self._validation_results: Dict[str, Any] = {}

        logger.info("DataValidator initialized")

    def _find_column(self, df: pd.DataFrame, target: str) -> Optional[str]:
        """Return actual column name in df matching target (case-insensitive)."""
        target_lower = target.lower()
        for col in df.columns:
            if str(col).lower() == target_lower:
                return str(col)
        return None

    def _find_columns(self, df: pd.DataFrame, targets: List[str]) -> Dict[str, str]:
        """Find multiple columns by name (case-insensitive)."""
        mapping = {}
        for target in targets:
            found = self._find_column(df, target)
            if found:
                mapping[target] = found
        return mapping

    def _get_time_series(self, df: pd.DataFrame) -> Optional[pd.Series]:
        """Get time series from DataFrame (index or column)."""
        if isinstance(df.index, pd.DatetimeIndex):
            return df.index.to_series()
        time_col = self._find_column(df, "datetime")
        if time_col:
            return pd.to_datetime(df[time_col])
        time_col = self._find_column(df, "time")
        if time_col:
            return pd.to_datetime(df[time_col])
        return None

    @staticmethod
    def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for backtesting (standardize column names, add spread if missing).

        Args:
            df: Raw OHLCV data

        Returns:
            DataFrame with standardized columns: open, high, low, close, volume, spread
            Index: DatetimeIndex (sorted ascending)

        Raises:
            ValueError: If required columns missing

        Example:
            >>> raw_data = pd.read_csv('data.csv')
            >>> data = DataValidator.prepare_data(raw_data)
            >>> print(data.columns)
            Index(['open', 'high', 'low', 'close', 'volume', 'spread'], dtype='object')
        """
        # Standardize column names to lowercase
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]

        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            datetime_cols = ["time", "datetime", "timestamp", "date"]
            for col in datetime_cols:
                if col in df.columns:
                    df.index = pd.DatetimeIndex(df[col])
                    df = df.drop(columns=[col])
                    logger.debug(f"Converted '{col}' column to DatetimeIndex")
                    break

        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError(
                "Could not create DatetimeIndex. "
                "Data must have DatetimeIndex or one of: time, datetime, timestamp, date"
            )

        # Add spread if missing (use 0 or estimate from bid-ask)
        if "spread" not in df.columns:
            if "bid" in df.columns and "ask" in df.columns:
                df["spread"] = df["ask"] - df["bid"]
                logger.debug("Calculated spread from bid-ask")
            else:
                df["spread"] = 0.0
                logger.debug("Added spread column with default value 0.0")

        # Ensure required columns exist
        required = ["open", "high", "low", "close", "volume", "spread"]
        missing = set(required) - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {missing}\n"
                f"Available columns: {list(df.columns)}"
            )

        # Sort by index
        df = df.sort_index()

        # Return only required columns
        return df[required]

    # ==================== Price Sanity Checks ====================

    def _check_high_low(
        self, df: pd.DataFrame, high_col: str, low_col: str
    ) -> List[Dict[str, Any]]:
        """Check that High >= Low."""
        issues = []
        if high_col and low_col:
            invalid = df[high_col] < df[low_col]
            if invalid.any():
                count = invalid.sum()
                issues.append(
                    {
                        "type": "price_sanity",
                        "check": "High >= Low",
                        "count": int(count),
                        "rows": df[invalid].index.tolist(),
                    }
                )
                df.loc[invalid, "_price_valid"] = False
                logger.warning(f"Found {count} rows where High < Low")
        return issues

    def _check_price_in_range(
        self,
        df: pd.DataFrame,
        price_col: str,
        low_col: str,
        high_col: str,
        check_name: str,
    ) -> List[Dict[str, Any]]:
        """Check that price column is within [Low, High] range."""
        issues = []
        if price_col and low_col and high_col:
            invalid = (df[price_col] < df[low_col]) | (df[price_col] > df[high_col])
            if invalid.any():
                count = invalid.sum()
                issues.append(
                    {
                        "type": "price_sanity",
                        "check": check_name,
                        "count": int(count),
                        "rows": df[invalid].index.tolist(),
                    }
                )
                df.loc[invalid, "_price_valid"] = False
                logger.warning(f"Found {count} rows where {check_name}")
        return issues

    def _check_negative_prices(
        self, df: pd.DataFrame, price_cols: List[str]
    ) -> List[Dict[str, Any]]:
        """Check for negative prices."""
        issues = []
        for col in price_cols:
            invalid = df[col] < 0
            if invalid.any():
                count = invalid.sum()
                issues.append(
                    {
                        "type": "price_sanity",
                        "check": f"No negative prices ({col})",
                        "count": int(count),
                        "rows": df[invalid].index.tolist(),
                    }
                )
                df.loc[invalid, "_price_valid"] = False
                logger.warning(f"Found {count} rows with negative prices in {col}")
        return issues

    def _check_zero_prices(
        self, df: pd.DataFrame, price_cols: List[str]
    ) -> List[Dict[str, Any]]:
        """Check for zero prices (warning only)."""
        issues = []
        for col in price_cols:
            invalid = df[col] == 0
            if invalid.any():
                count = invalid.sum()
                issues.append(
                    {
                        "type": "price_sanity",
                        "check": f"No zero prices ({col})",
                        "count": int(count),
                        "rows": df[invalid].index.tolist(),
                        "severity": "warning",  # May be valid for some instruments
                    }
                )
                logger.warning(f"Found {count} rows with zero prices in {col}")
        return issues

    def validate_price_sanity(
        self, data: pd.DataFrame, mark_invalid: bool = False
    ) -> Tuple[bool, pd.DataFrame, List[Dict[str, Any]]]:
        """
        Validate price sanity checks for OHLCV data.

        Checks:
        - High >= Low
        - Close within [Low, High]
        - Open within [Low, High]
        - No negative prices
        - No zero prices (unless expected)

        Args:
            data: DataFrame with OHLCV data
            mark_invalid: If True, adds 'is_valid' column marking invalid rows

        Returns:
            Tuple of (all_valid, dataframe_with_marks, list_of_issues)
        """
        df = data.copy()
        issues = []

        # Find OHLC columns
        ohlc_mapping = self._find_columns(df, ["Open", "High", "Low", "Close"])
        if not ohlc_mapping:
            return False, df, [{"type": "error", "message": "No OHLC columns found"}]

        open_col = ohlc_mapping.get("Open")
        high_col = ohlc_mapping.get("High")
        low_col = ohlc_mapping.get("Low")
        close_col = ohlc_mapping.get("Close")

        # Initialize validity column
        df["_price_valid"] = True

        # Run all checks
        if high_col and low_col:
            issues.extend(self._check_high_low(df, high_col, low_col))
        if close_col and low_col and high_col:
            issues.extend(
                self._check_price_in_range(
                    df, close_col, low_col, high_col, "Close within [Low, High]"
                )
            )
        if open_col and low_col and high_col:
            issues.extend(
                self._check_price_in_range(
                    df, open_col, low_col, high_col, "Open within [Low, High]"
                )
            )

        price_cols = [c for c in [open_col, high_col, low_col, close_col] if c]
        issues.extend(self._check_negative_prices(df, price_cols))
        issues.extend(self._check_zero_prices(df, price_cols))

        all_valid = len(issues) == 0

        if mark_invalid:
            df["is_valid"] = df["_price_valid"]
        df = df.drop(columns=["_price_valid"], errors="ignore")

        return all_valid, df, issues

    # ==================== Gap Detection ====================

    def detect_gaps(
        self,
        data: pd.DataFrame,
        expected_frequency: Optional[Union[str, timedelta]] = None,
        tolerance: float = 1.5,
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Detect gaps in time series data.

        Args:
            data: DataFrame with datetime index or time column
            expected_frequency: Expected frequency (e.g., '1H', '5T', timedelta)
            tolerance: Multiplier for expected frequency to detect gaps (default: 1.5)

        Returns:
            Tuple of (gaps_dataframe, list_of_gap_info)
        """
        time_series = self._get_time_series(data)
        if time_series is None:
            logger.error(
                "Data must have a datetime index or time column for gap detection"
            )
            return pd.DataFrame(), []

        # Sort by time
        time_df = pd.DataFrame({"Datetime": pd.to_datetime(time_series.values)})
        time_df = time_df.sort_values("Datetime")
        time_df["time_diff"] = time_df["Datetime"].diff()

        gap_info = []

        # If expected frequency provided, use it
        if expected_frequency:
            if isinstance(expected_frequency, str):
                # Convert deprecated 'H' to 'h' for hours
                freq_str = expected_frequency.replace("H", "h")
                expected_diff = pd.Timedelta(freq_str)
            else:
                expected_diff = expected_frequency
        else:
            # Infer from most common difference
            mode_diff = time_df["time_diff"].mode()
            if len(mode_diff) > 0:
                expected_diff = mode_diff.iloc[0]
            else:
                expected_diff = time_df["time_diff"].median()

        threshold = expected_diff * tolerance
        gap_rows = time_df[time_df["time_diff"] > threshold]

        for _idx, row in gap_rows.iterrows():
            gap_start = row["Datetime"] - row["time_diff"]
            gap_end = row["Datetime"]
            gap_duration = row["time_diff"]
            expected_periods = int(gap_duration / expected_diff)

            gap_info.append(
                {
                    "gap_start": gap_start,
                    "gap_end": gap_end,
                    "duration": gap_duration,
                    "expected_periods": expected_periods,
                    "actual_diff": gap_duration,
                    "expected_diff": expected_diff,
                }
            )

        logger.info(f"Detected {len(gap_info)} gaps in data")
        return gap_rows, gap_info

    # ==================== Spike Detection / Anomaly Marking ====================

    def detect_spikes(  # noqa: C901
        self,
        data: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = "zscore",
        mark_anomalies: bool = True,
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Detect spikes and anomalies in price data.

        Args:
            data: DataFrame with price data
            columns: Columns to check (default: all OHLC columns)
            method: Detection method ('zscore', 'iqr', 'mad', or 'both')
            mark_anomalies: If True, adds 'is_anomaly' column

        Returns:
            Tuple of (dataframe_with_marks, list_of_anomalies)
        """
        df = data.copy()
        anomalies = []

        # Find columns to check
        if columns is None:
            ohlc_mapping = self._find_columns(df, ["Open", "High", "Low", "Close"])
            columns = list(ohlc_mapping.values())

        if not columns:
            logger.warning("No columns found for spike detection")
            return df, []

        df["_is_anomaly"] = False

        for col in columns:
            if col not in df.columns:
                continue

            col_data = df[col].dropna()

            if method in ["zscore", "both"]:
                z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                z_anomalies = z_scores > self.z_score_threshold

                if z_anomalies.any():
                    anomaly_rows = col_data[z_anomalies].index.tolist()
                    anomalies.append(
                        {
                            "type": "spike",
                            "method": "zscore",
                            "column": col,
                            "count": len(anomaly_rows),
                            "rows": anomaly_rows,
                            "threshold": self.z_score_threshold,
                        }
                    )
                    df.loc[anomaly_rows, "_is_anomaly"] = True
                    logger.info(
                        f"Detected {len(anomaly_rows)} Z-score anomalies in {col}"
                    )

            if method in ["iqr", "both"]:
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.iqr_multiplier * IQR
                upper_bound = Q3 + self.iqr_multiplier * IQR

                iqr_anomalies = (col_data < lower_bound) | (col_data > upper_bound)

                if iqr_anomalies.any():
                    anomaly_rows = col_data[iqr_anomalies].index.tolist()
                    anomalies.append(
                        {
                            "type": "spike",
                            "method": "iqr",
                            "column": col,
                            "count": len(anomaly_rows),
                            "rows": anomaly_rows,
                            "lower_bound": float(lower_bound),
                            "upper_bound": float(upper_bound),
                        }
                    )
                    df.loc[anomaly_rows, "_is_anomaly"] = True
                    logger.info(f"Detected {len(anomaly_rows)} IQR anomalies in {col}")

            if method == "mad":
                # Median Absolute Deviation method
                median = col_data.median()
                mad = np.median(np.abs(col_data - median))
                if mad == 0:
                    logger.warning(f"MAD is zero for {col}, skipping MAD detection")
                    continue

                # Modified Z-score using MAD
                modified_z_scores = 0.6745 * (col_data - median) / mad
                mad_anomalies = np.abs(modified_z_scores) > self.z_score_threshold

                if mad_anomalies.any():
                    anomaly_rows = col_data[mad_anomalies].index.tolist()
                    anomalies.append(
                        {
                            "type": "spike",
                            "method": "mad",
                            "column": col,
                            "count": len(anomaly_rows),
                            "rows": anomaly_rows,
                            "median": float(median),
                            "mad": float(mad),
                            "threshold": self.z_score_threshold,
                        }
                    )
                    df.loc[anomaly_rows, "_is_anomaly"] = True
                    logger.info(f"Detected {len(anomaly_rows)} MAD anomalies in {col}")

        if mark_anomalies:
            df["is_anomaly"] = df["_is_anomaly"]
        df = df.drop(columns=["_is_anomaly"], errors="ignore")

        return df, anomalies

    # ==================== Missing Timestamps Checker ====================

    def _infer_frequency(self, timestamps: pd.Series) -> Optional[timedelta]:
        """Infer frequency from timestamp differences."""
        diffs = pd.Series(timestamps).diff().dropna()
        if len(diffs) == 0:
            logger.warning("Cannot infer frequency from single timestamp")
            return None

        mode_diff = diffs.mode()
        if len(mode_diff) > 0 and pd.notna(mode_diff.iloc[0]):
            return cast(timedelta, pd.Timedelta(mode_diff.iloc[0]).to_pytimedelta())

        median_diff = diffs.median()
        if pd.notna(median_diff):
            return cast(timedelta, pd.Timedelta(median_diff).to_pytimedelta())

        logger.warning("Cannot infer frequency from timestamp differences")
        return None

    def _normalize_frequency(
        self, expected_frequency: Optional[Union[str, timedelta]]
    ) -> Optional[pd.Timedelta]:
        """Normalize frequency to pd.Timedelta."""
        if expected_frequency is None:
            return None

        if isinstance(expected_frequency, str):
            # Convert deprecated 'H' to 'h' for hours
            freq_str = expected_frequency.replace("H", "h")
            return pd.Timedelta(freq_str)

        if pd.isna(expected_frequency):
            logger.warning("Invalid frequency (NaT), cannot check missing timestamps")
            return None

        # Convert timedelta to pd.Timedelta
        return pd.Timedelta(expected_frequency)

    def check_missing_timestamps(
        self,
        data: pd.DataFrame,
        expected_frequency: Optional[Union[str, timedelta]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Check for missing timestamps in time series data.

        Args:
            data: DataFrame with datetime index or time column
            expected_frequency: Expected frequency (e.g., '1H', '5T', timedelta)
            start_date: Start date for expected range (default: first timestamp)
            end_date: End date for expected range (default: last timestamp)

        Returns:
            Tuple of (missing_timestamps_dataframe, list_of_missing_info)
        """
        time_series = self._get_time_series(data)
        if time_series is None:
            logger.error(
                "Data must have a datetime index or time column for missing timestamp check"
            )
            return pd.DataFrame(), []

        timestamps = pd.to_datetime(time_series.values)
        timestamps = pd.Series(timestamps).sort_values().unique()

        # Determine expected range
        if start_date is None:
            first_ts = timestamps[0]
            if pd.isna(first_ts):
                start_date = datetime.now()
            else:
                start_date = pd.Timestamp(first_ts).to_pydatetime()
        if end_date is None:
            last_ts = timestamps[-1]
            if pd.isna(last_ts):
                end_date = datetime.now()
            else:
                end_date = pd.Timestamp(last_ts).to_pydatetime()

        # Determine expected frequency
        if expected_frequency is None:
            inferred_freq = self._infer_frequency(pd.Series(timestamps))
            if inferred_freq is None:
                return pd.DataFrame(), []
            expected_frequency = inferred_freq

        freq = self._normalize_frequency(expected_frequency)
        if freq is None:
            return pd.DataFrame(), []

        # Generate expected timestamps
        expected_range = pd.date_range(start=start_date, end=end_date, freq=freq)
        expected_set = set(expected_range)
        actual_set = set(timestamps)

        missing_timestamps = sorted(expected_set - actual_set)
        missing_info = []

        if missing_timestamps:
            missing_df = pd.DataFrame({"MissingTimestamp": missing_timestamps})
            missing_info.append(
                {
                    "type": "missing_timestamps",
                    "count": len(missing_timestamps),
                    "expected_total": len(expected_range),
                    "actual_total": len(timestamps),
                    "coverage": len(actual_set & expected_set) / len(expected_set),
                    "missing_timestamps": missing_timestamps[
                        :100
                    ],  # Limit to first 100
                }
            )
            logger.warning(
                f"Found {len(missing_timestamps)} missing timestamps out of {len(expected_range)} expected"
            )
            return missing_df, missing_info

        logger.info("No missing timestamps found")
        return pd.DataFrame(), []

    # ==================== Zero Volume Detection ====================

    def detect_zero_volume(
        self, data: pd.DataFrame, threshold: float = 0.0
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Detect bars with zero or very low volume.

        Args:
            data: DataFrame with volume data
            threshold: Volume threshold (default: 0.0)

        Returns:
            Tuple of (zero_volume_dataframe, list_of_issues)
        """
        df = data.copy()
        volume_col = self._find_column(df, "volume")

        if not volume_col:
            logger.warning("No volume column found")
            return pd.DataFrame(), []

        zero_volume = df[df[volume_col] <= threshold]
        issues = []

        if len(zero_volume) > 0:
            issues.append(
                {
                    "type": "zero_volume",
                    "count": len(zero_volume),
                    "rows": zero_volume.index.tolist(),
                    "threshold": threshold,
                }
            )
            logger.warning(f"Found {len(zero_volume)} bars with volume <= {threshold}")

        return zero_volume, issues

    # ==================== Duplicate Detection ====================

    def detect_duplicates(
        self, data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Detect duplicate timestamps in data.

        Args:
            data: DataFrame with datetime index or time column

        Returns:
            Tuple of (duplicates_dataframe, list_of_issues)
        """
        time_series = self._get_time_series(data)
        if time_series is None:
            logger.error("Data must have a datetime index or time column")
            return pd.DataFrame(), []

        duplicates = time_series[time_series.duplicated(keep=False)]
        issues = []

        if len(duplicates) > 0:
            dup_df = data.loc[duplicates.index]
            unique_dup_timestamps = duplicates.unique()

            issues.append(
                {
                    "type": "duplicates",
                    "count": len(duplicates),
                    "unique_timestamps": len(unique_dup_timestamps),
                    "timestamps": unique_dup_timestamps.tolist()[:100],  # Limit to 100
                }
            )
            logger.warning(
                f"Found {len(duplicates)} duplicate rows across {len(unique_dup_timestamps)} unique timestamps"
            )
            return dup_df, issues

        logger.info("No duplicate timestamps found")
        return pd.DataFrame(), []

    def check_monotonic_timestamps(
        self, data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Check that timestamps are monotonic non-decreasing.

        Args:
            data: DataFrame with datetime index or time column

        Returns:
            Tuple of (non_monotonic_rows_dataframe, list_of_issues)
        """
        time_series = self._get_time_series(data)
        if time_series is None:
            logger.error("Data must have a datetime index or time column")
            return pd.DataFrame(), []

        timestamps = pd.Series(pd.to_datetime(time_series.values))
        if len(timestamps) <= 1:
            return pd.DataFrame(), []

        # Non-monotonic points are where the current timestamp is earlier than previous.
        disorder_mask = timestamps < timestamps.shift(1)
        disorder_idx = disorder_mask[disorder_mask].index

        if len(disorder_idx) > 0:
            issue = {
                "type": "monotonic_timestamps",
                "check": "timestamps_non_decreasing",
                "count": int(len(disorder_idx)),
                "positions": disorder_idx.astype(int).tolist()[:100],
            }
            logger.warning(
                f"Found {len(disorder_idx)} non-monotonic timestamp transitions"
            )
            return data.iloc[disorder_idx], [issue]

        logger.info("Timestamps are monotonic non-decreasing")
        return pd.DataFrame(), []

    # ==================== Spread Analysis ====================

    def analyze_spread(
        self, data: pd.DataFrame
    ) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        """
        Analyze spread statistics.

        Args:
            data: DataFrame with spread data (or bid/ask)

        Returns:
            Tuple of (spread_statistics, list_of_issues)
        """
        df = data.copy()
        spread_col = self._find_column(df, "spread")

        if not spread_col:
            # Try to calculate from bid/ask
            bid_col = self._find_column(df, "bid")
            ask_col = self._find_column(df, "ask")
            if bid_col and ask_col:
                df["_spread"] = df[ask_col] - df[bid_col]
                spread_col = "_spread"
            else:
                logger.warning("No spread, bid, or ask columns found")
                return {}, []

        spread_data = df[spread_col].dropna()

        if len(spread_data) == 0:
            return {}, []

        stats = {
            "mean": float(spread_data.mean()),
            "median": float(spread_data.median()),
            "std": float(spread_data.std()),
            "min": float(spread_data.min()),
            "max": float(spread_data.max()),
            "q25": float(spread_data.quantile(0.25)),
            "q75": float(spread_data.quantile(0.75)),
        }

        issues = []

        # Check for negative spreads (should not happen)
        negative_spreads = spread_data[spread_data < 0]
        if len(negative_spreads) > 0:
            issues.append(
                {
                    "type": "spread_anomaly",
                    "issue": "negative_spread",
                    "count": len(negative_spreads),
                    "rows": negative_spreads.index.tolist(),
                }
            )
            logger.warning(f"Found {len(negative_spreads)} bars with negative spread")

        # Check for unusually wide spreads (> Q3 + 3*IQR)
        Q1 = spread_data.quantile(0.25)
        Q3 = spread_data.quantile(0.75)
        IQR = Q3 - Q1
        upper_threshold = Q3 + 3 * IQR
        wide_spreads = spread_data[spread_data > upper_threshold]

        if len(wide_spreads) > 0:
            issues.append(
                {
                    "type": "spread_anomaly",
                    "issue": "wide_spread",
                    "count": len(wide_spreads),
                    "threshold": float(upper_threshold),
                    "rows": wide_spreads.index.tolist()[:100],  # Limit to 100
                }
            )
            logger.info(f"Found {len(wide_spreads)} bars with unusually wide spread")

        logger.info(f"Spread analysis complete: mean={stats['mean']:.5f}")
        return stats, issues

    # ==================== Data Cleaning ====================

    def clean_data(  # noqa: C901
        self,
        data: pd.DataFrame,
        remove_duplicates: bool = True,
        remove_invalid_prices: bool = True,
        remove_anomalies: bool = False,
        remove_zero_volume: bool = False,
        fill_gaps: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Clean data based on validation issues.

        Args:
            data: DataFrame to clean
            remove_duplicates: Remove duplicate timestamps
            remove_invalid_prices: Remove rows with invalid OHLC relationships
            remove_anomalies: Remove detected anomalies/spikes
            remove_zero_volume: Remove zero volume bars
            fill_gaps: Fill gaps with forward fill (experimental)

        Returns:
            Tuple of (cleaned_dataframe, cleaning_stats)
        """
        df = data.copy()
        stats = {
            "original_rows": len(df),
            "duplicates_removed": 0,
            "invalid_prices_removed": 0,
            "anomalies_removed": 0,
            "zero_volume_removed": 0,
            "gaps_filled": 0,
        }

        # Remove duplicates
        if remove_duplicates:
            time_series = self._get_time_series(df)
            if time_series is not None:
                before = len(df)
                df = df[~time_series.duplicated(keep="first")]
                stats["duplicates_removed"] = before - len(df)
                logger.info(f"Removed {stats['duplicates_removed']} duplicate rows")

        # Remove invalid prices
        if remove_invalid_prices:
            before = len(df)
            all_valid, df_marked, _ = self.validate_price_sanity(df, mark_invalid=True)
            if "is_valid" in df_marked.columns:
                df = df_marked[df_marked["is_valid"]].drop(columns=["is_valid"])
                stats["invalid_prices_removed"] = before - len(df)
                logger.info(
                    f"Removed {stats['invalid_prices_removed']} invalid price rows"
                )

        # Remove anomalies
        if remove_anomalies:
            before = len(df)
            df_marked, _ = self.detect_spikes(df, method="both", mark_anomalies=True)
            if "is_anomaly" in df_marked.columns:
                df = df_marked[~df_marked["is_anomaly"]].drop(columns=["is_anomaly"])
                stats["anomalies_removed"] = before - len(df)
                logger.info(f"Removed {stats['anomalies_removed']} anomaly rows")

        # Remove zero volume
        if remove_zero_volume:
            volume_col = self._find_column(df, "volume")
            if volume_col:
                before = len(df)
                df = df[df[volume_col] > 0]
                stats["zero_volume_removed"] = before - len(df)
                logger.info(f"Removed {stats['zero_volume_removed']} zero volume rows")

        # Fill gaps (experimental)
        if fill_gaps:
            time_series = self._get_time_series(df)
            if time_series is not None and isinstance(df.index, pd.DatetimeIndex):
                before = len(df)
                # Infer frequency and resample
                inferred_freq = self._infer_frequency(time_series)
                if inferred_freq:
                    df = df.resample(inferred_freq).ffill()
                    stats["gaps_filled"] = len(df) - before
                    logger.info(f"Filled {stats['gaps_filled']} gap rows")

        stats["final_rows"] = len(df)
        stats["total_removed"] = stats["original_rows"] - stats["final_rows"]

        logger.info(
            f"Data cleaning complete: {stats['original_rows']} -> {stats['final_rows']} rows "
            f"({stats['total_removed']} removed)"
        )
        return df, stats

    # ==================== Comprehensive Validation ====================

    def validate(
        self,
        data: pd.DataFrame,
        checks: Optional[List[str]] = None,
        return_report: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], DataQualityReport]:
        """
        Run comprehensive data validation.

        Args:
            data: DataFrame with market data
            checks: List of checks to run (default: all)
                   Options: 'monotonic_timestamps', 'normalized_schema',
                           'price_sanity', 'gaps', 'spikes', 'missing_timestamps',
                           'zero_volume', 'duplicates', 'spread'
            return_report: If True, return DataQualityReport instead of dict
            **kwargs: Additional parameters for specific checks

        Returns:
            Dictionary or DataQualityReport with validation results
        """
        if checks is None:
            checks = [
                "monotonic_timestamps",
                "normalized_schema",
                "price_sanity",
                "gaps",
                "spikes",
                "missing_timestamps",
                "zero_volume",
                "duplicates",
                "spread",
            ]

        results: Dict[str, Any] = {
            "timestamp": datetime.now(),
            "total_rows": len(data),
            "checks_performed": [],
            "issues_found": [],
            "summary": {},
        }

        # Monotonic timestamp check (run before normalization so input ordering issues are visible).
        if "monotonic_timestamps" in checks:
            logger.info("Checking timestamp monotonicity...")
            non_monotonic_df, monotonic_issues = self.check_monotonic_timestamps(data)
            results["checks_performed"].append("monotonic_timestamps")
            results["issues_found"].extend(monotonic_issues)
            results["summary"]["monotonic_timestamps"] = {
                "is_monotonic": len(monotonic_issues) == 0,
                "disorder_count": (
                    monotonic_issues[0]["count"] if monotonic_issues else 0
                ),
            }

        # Schema normalization / standardization
        if "normalized_schema" in checks:
            logger.info("Running schema normalization check...")
            try:
                data = self.prepare_data(data)
                results["checks_performed"].append("normalized_schema")
                results["summary"]["normalized_schema"] = {
                    "valid": True,
                    "columns": list(data.columns),
                    "rows": len(data),
                }
            except Exception as exc:
                issue = {
                    "type": "schema_validation",
                    "check": "prepare_data",
                    "count": 1,
                    "message": str(exc),
                }
                results["checks_performed"].append("normalized_schema")
                results["issues_found"].append(issue)
                results["summary"]["normalized_schema"] = {
                    "valid": False,
                    "message": str(exc),
                }
                results["summary"]["total_issues"] = 1
                results["summary"]["quality_score"] = 0.0
                results["summary"]["is_valid"] = False
                self._validation_results = results

                if return_report:
                    return DataQualityReport(
                        timestamp=results["timestamp"],
                        total_rows=results["total_rows"],
                        checks_performed=results["checks_performed"],
                        issues_found=results["issues_found"],
                        summary=results["summary"],
                        quality_score=results["summary"]["quality_score"],
                        is_valid=results["summary"]["is_valid"],
                    )
                return results

        # Price sanity checks
        if "price_sanity" in checks:
            logger.info("Running price sanity checks...")
            all_valid, df_marked, issues = self.validate_price_sanity(
                data, mark_invalid=kwargs.get("mark_invalid", False)
            )
            results["checks_performed"].append("price_sanity")
            results["issues_found"].extend(issues)
            results["summary"]["price_sanity"] = {
                "all_valid": all_valid,
                "issues_count": len(issues),
            }

        # Gap detection
        if "gaps" in checks:
            logger.info("Running gap detection...")
            gaps_df, gap_info = self.detect_gaps(
                data,
                expected_frequency=kwargs.get("expected_frequency"),
                tolerance=kwargs.get("tolerance", 1.5),
            )
            results["checks_performed"].append("gaps")
            results["issues_found"].extend(
                [{"type": "gap", **info} for info in gap_info]
            )
            results["summary"]["gaps"] = {
                "gaps_count": len(gap_info),
                "gaps": gap_info,
            }

        # Spike detection
        if "spikes" in checks:
            logger.info("Running spike detection...")
            df_marked, anomalies = self.detect_spikes(
                data,
                columns=kwargs.get("columns"),
                method=kwargs.get("method", "zscore"),
                mark_anomalies=kwargs.get("mark_anomalies", True),
            )
            results["checks_performed"].append("spikes")
            results["issues_found"].extend(anomalies)
            results["summary"]["spikes"] = {
                "anomalies_count": len(anomalies),
                "anomalies": anomalies,
            }

        # Missing timestamps
        if "missing_timestamps" in checks:
            logger.info("Checking for missing timestamps...")
            missing_df, missing_info = self.check_missing_timestamps(
                data,
                expected_frequency=kwargs.get("expected_frequency"),
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
            )
            results["checks_performed"].append("missing_timestamps")
            results["issues_found"].extend(missing_info)
            results["summary"]["missing_timestamps"] = {
                "missing_count": missing_info[0]["count"] if missing_info else 0,
                "coverage": missing_info[0]["coverage"] if missing_info else 1.0,
            }

        # Zero volume detection
        if "zero_volume" in checks:
            logger.info("Checking for zero volume bars...")
            zero_vol_df, zero_vol_issues = self.detect_zero_volume(
                data, threshold=kwargs.get("volume_threshold", 0.0)
            )
            results["checks_performed"].append("zero_volume")
            results["issues_found"].extend(zero_vol_issues)
            results["summary"]["zero_volume"] = {
                "zero_volume_count": (
                    zero_vol_issues[0]["count"] if zero_vol_issues else 0
                ),
            }

        # Duplicate detection
        if "duplicates" in checks:
            logger.info("Checking for duplicate timestamps...")
            dup_df, dup_issues = self.detect_duplicates(data)
            results["checks_performed"].append("duplicates")
            results["issues_found"].extend(dup_issues)
            results["summary"]["duplicates"] = {
                "duplicates_count": dup_issues[0]["count"] if dup_issues else 0,
                "unique_duplicates": (
                    dup_issues[0]["unique_timestamps"] if dup_issues else 0
                ),
            }

        # Spread analysis
        if "spread" in checks:
            logger.info("Analyzing spread statistics...")
            spread_stats, spread_issues = self.analyze_spread(data)
            results["checks_performed"].append("spread")
            results["issues_found"].extend(spread_issues)
            results["summary"]["spread"] = {
                "spread_stats": spread_stats,
                "spread_issues_count": len(spread_issues),
            }

        # Calculate overall quality score
        total_issues = len(results["issues_found"])
        results["summary"]["total_issues"] = total_issues
        results["summary"]["quality_score"] = max(
            0, 100 - (total_issues / max(1, results["total_rows"]) * 100)
        )
        results["summary"]["is_valid"] = total_issues == 0

        self._validation_results = results

        # Return DataQualityReport if requested
        if return_report:
            return DataQualityReport(
                timestamp=results["timestamp"],
                total_rows=results["total_rows"],
                checks_performed=results["checks_performed"],
                issues_found=results["issues_found"],
                summary=results["summary"],
                quality_score=results["summary"]["quality_score"],
                is_valid=results["summary"]["is_valid"],
                price_sanity_valid=results["summary"]
                .get("price_sanity", {})
                .get("all_valid", True),
                gaps_count=results["summary"].get("gaps", {}).get("gaps_count", 0),
                anomalies_count=results["summary"]
                .get("spikes", {})
                .get("anomalies_count", 0),
                missing_timestamps_count=results["summary"]
                .get("missing_timestamps", {})
                .get("missing_count", 0),
                zero_volume_count=results["summary"]
                .get("zero_volume", {})
                .get("zero_volume_count", 0),
                duplicates_count=results["summary"]
                .get("duplicates", {})
                .get("duplicates_count", 0),
                spread_stats=results["summary"].get("spread", {}).get("spread_stats"),
            )

        return results

    # ==================== Validation Reporting ====================

    def _generate_text_report(self, results: Dict[str, Any]) -> str:
        """Generate text format report."""
        report_lines = [
            "=" * 60,
            "DATA VALIDATION REPORT",
            "=" * 60,
            f"Timestamp: {results['timestamp']}",
            f"Total Rows: {results['total_rows']}",
            f"Checks Performed: {', '.join(results['checks_performed'])}",
            "",
            "SUMMARY",
            "-" * 60,
            f"Total Issues Found: {results['summary']['total_issues']}",
            f"Quality Score: {results['summary']['quality_score']:.2f}%",
            f"Overall Status: {'VALID' if results['summary']['is_valid'] else 'INVALID'}",
            "",
        ]

        # Add details for each check
        for check in results["checks_performed"]:
            check_summary = results["summary"].get(check, {})
            report_lines.append(f"{check.upper()}")
            report_lines.append("-" * 60)
            if isinstance(check_summary, dict):
                for key, value in check_summary.items():
                    if key not in ["gaps", "anomalies"]:  # Skip detailed lists
                        report_lines.append(f"  {key}: {value}")
            report_lines.append("")

        # Add issues list
        if results["issues_found"]:
            report_lines.append("ISSUES DETAILS")
            report_lines.append("-" * 60)
            for i, issue in enumerate(results["issues_found"][:20], 1):  # Limit to 20
                report_lines.append(
                    f"{i}. {issue.get('type', 'unknown')}: {issue.get('message', issue)}"
                )

        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    def _generate_json_report(self, results: Dict[str, Any]) -> str:
        """Generate JSON format report."""
        import json

        return json.dumps(results, default=str, indent=2)

    def generate_report(
        self, results: Optional[Dict[str, Any]] = None, format: str = "dict"
    ) -> Union[Dict[str, Any], str]:
        """
        Generate validation report.

        Args:
            results: Validation results (default: use last validation)
            format: Report format ('dict', 'text', 'json')

        Returns:
            Report in requested format
        """
        if results is None:
            results = self._validation_results

        if not results:
            return "No validation results available"

        if format == "dict":
            return results
        elif format == "text":
            return self._generate_text_report(results)
        elif format == "json":
            return self._generate_json_report(results)
        else:
            raise ValueError(f"Unknown format: {format}")

    def export_report(
        self,
        filepath: Union[str, Path],
        results: Optional[Dict[str, Any]] = None,
        format: str = "json",
    ):
        """
        Export validation report to file.

        Args:
            filepath: Path to output file
            results: Validation results (default: use last validation)
            format: File format ('json', 'txt')
        """
        if results is None:
            results = self._validation_results

        output_path = ensure_parent_dir(filepath)

        if format == "json":
            import json

            with output_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, default=str, indent=2)
        elif format == "txt":
            report_text = self.generate_report(results, format="text")
            if isinstance(report_text, str):
                with output_path.open("w", encoding="utf-8") as f:
                    f.write(report_text)
            else:
                raise ValueError("Expected string report but got dict")
        else:
            raise ValueError(f"Unknown format: {format}")

        logger.info(f"Validation report exported to {output_path}")

    # ==================== Visualization ====================

    def plot_data_quality_report(
        self,
        results: Optional[Union[Dict[str, Any], DataQualityReport]] = None,
        figsize: Tuple[int, int] = (14, 10),
        save_path: Optional[str] = None,
    ):
        """
        Plot data quality report with visualizations.

        Creates a comprehensive dashboard showing:
        - Quality score gauge
        - Issues breakdown
        - Checks performed
        - Detailed metrics

        Args:
            results: Validation results (default: use last validation)
            figsize: Figure size
            save_path: Path to save figure (optional)

        Requires:
            matplotlib
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.error(
                "matplotlib is required for plotting. Install with: pip install matplotlib"
            )
            return

        if results is None:
            results = self._validation_results

        if not results:
            logger.warning("No validation results available")
            return

        # Convert DataQualityReport to dict if needed
        if isinstance(results, DataQualityReport):
            results_dict = results.to_dict()
        else:
            results_dict = results

        fig, axes = plt.subplots(2, 2, figsize=figsize)
        fig.suptitle("Data Quality Validation Report", fontsize=16, fontweight="bold")

        # 1. Quality Score Gauge (top-left)
        ax1 = axes[0, 0]
        quality_score = results_dict["summary"]["quality_score"]
        self._plot_quality_gauge(ax1, quality_score)

        # 2. Issues Breakdown (top-right)
        ax2 = axes[0, 1]
        self._plot_issues_breakdown(ax2, results_dict)

        # 3. Checks Summary (bottom-left)
        ax3 = axes[1, 0]
        self._plot_checks_summary(ax3, results_dict)

        # 4. Detailed Metrics (bottom-right)
        ax4 = axes[1, 1]
        self._plot_detailed_metrics(ax4, results_dict)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"Quality report plot saved to {save_path}")
        else:
            plt.show()

    def _plot_quality_gauge(self, ax, quality_score: float):
        """Plot quality score as a gauge."""
        from matplotlib.patches import Circle, Wedge

        # Determine color based on score
        if quality_score >= 90:
            color = "green"
            status = "EXCELLENT"
        elif quality_score >= 75:
            color = "yellowgreen"
            status = "GOOD"
        elif quality_score >= 50:
            color = "orange"
            status = "FAIR"
        else:
            color = "red"
            status = "POOR"

        # Draw gauge
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Background circle
        circle = Circle((0.5, 0.5), 0.35, color="lightgray", alpha=0.3)
        ax.add_patch(circle)

        # Score arc
        wedge = Wedge(
            (0.5, 0.5),
            0.35,
            0,
            quality_score * 3.6,
            facecolor=color,
            edgecolor=color,
            linewidth=3,
        )
        ax.add_patch(wedge)

        # Text
        ax.text(
            0.5,
            0.5,
            f"{quality_score:.1f}%",
            ha="center",
            va="center",
            fontsize=32,
            fontweight="bold",
        )
        ax.text(
            0.5,
            0.3,
            status,
            ha="center",
            va="center",
            fontsize=14,
            color=color,
            fontweight="bold",
        )
        ax.set_title("Quality Score", fontsize=12, fontweight="bold", pad=20)

    def _plot_issues_breakdown(self, ax, results: Dict[str, Any]):
        """Plot issues breakdown as bar chart."""
        summary = results["summary"]

        issue_types = []
        issue_counts = []

        if "price_sanity" in summary:
            issue_types.append("Price\nSanity")
            issue_counts.append(summary["price_sanity"].get("issues_count", 0))

        if "gaps" in summary:
            issue_types.append("Gaps")
            issue_counts.append(summary["gaps"].get("gaps_count", 0))

        if "spikes" in summary:
            issue_types.append("Anomalies")
            issue_counts.append(summary["spikes"].get("anomalies_count", 0))

        if "missing_timestamps" in summary:
            issue_types.append("Missing\nTimestamps")
            issue_counts.append(summary["missing_timestamps"].get("missing_count", 0))

        if "zero_volume" in summary:
            issue_types.append("Zero\nVolume")
            issue_counts.append(summary["zero_volume"].get("zero_volume_count", 0))

        if "duplicates" in summary:
            issue_types.append("Duplicates")
            issue_counts.append(summary["duplicates"].get("duplicates_count", 0))

        if not issue_types:
            ax.text(
                0.5,
                0.5,
                "No issues to display",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title("Issues Breakdown", fontsize=12, fontweight="bold")
            ax.axis("off")
            return

        colors = ["red" if count > 0 else "green" for count in issue_counts]
        ax.barh(issue_types, issue_counts, color=colors, alpha=0.7)
        ax.set_xlabel("Count", fontsize=10)
        ax.set_title("Issues Breakdown", fontsize=12, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)

    def _plot_checks_summary(self, ax, results: Dict[str, Any]):
        """Plot checks performed as a table."""
        checks = results["checks_performed"]
        total_issues = results["summary"]["total_issues"]
        total_rows = results["total_rows"]

        # Create summary table
        table_data = [
            ["Total Rows", f"{total_rows:,}"],
            ["Checks Performed", len(checks)],
            ["Total Issues", total_issues],
            ["Valid", "Yes" if results["summary"]["is_valid"] else "No"],
        ]

        ax.axis("off")
        table = ax.table(
            cellText=table_data,
            colLabels=["Metric", "Value"],
            cellLoc="left",
            loc="center",
            colWidths=[0.6, 0.4],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)

        # Color the header
        for i in range(2):
            table[(0, i)].set_facecolor("#4CAF50")
            table[(0, i)].set_text_props(weight="bold", color="white")

        ax.set_title("Validation Summary", fontsize=12, fontweight="bold")

    def _plot_detailed_metrics(self, ax, results: Dict[str, Any]):
        """Plot detailed metrics as text."""
        ax.axis("off")

        summary = results["summary"]
        metrics_text = []

        # Add timestamp
        metrics_text.append(f"Timestamp: {results['timestamp']}")
        metrics_text.append("")

        # Add metrics for each check
        if "price_sanity" in summary:
            ps = summary["price_sanity"]
            metrics_text.append(
                f"Price Sanity: {'PASS' if ps.get('all_valid', False) else 'FAIL'}"
            )

        if "gaps" in summary:
            gaps = summary["gaps"]
            metrics_text.append(f"Gaps Detected: {gaps.get('gaps_count', 0)}")

        if "spikes" in summary:
            spikes = summary["spikes"]
            metrics_text.append(f"Anomalies: {spikes.get('anomalies_count', 0)}")

        if "missing_timestamps" in summary:
            mt = summary["missing_timestamps"]
            coverage = mt.get("coverage", 1.0) * 100
            metrics_text.append(f"Coverage: {coverage:.1f}%")

        if "zero_volume" in summary:
            zv = summary["zero_volume"]
            metrics_text.append(f"Zero Volume Bars: {zv.get('zero_volume_count', 0)}")

        if "duplicates" in summary:
            dup = summary["duplicates"]
            metrics_text.append(f"Duplicate Rows: {dup.get('duplicates_count', 0)}")

        if "spread" in summary and summary["spread"].get("spread_stats"):
            spread_stats = summary["spread"]["spread_stats"]
            metrics_text.append("")
            metrics_text.append("Spread Statistics:")
            metrics_text.append(f"  Mean: {spread_stats.get('mean', 0):.5f}")
            metrics_text.append(f"  Median: {spread_stats.get('median', 0):.5f}")
            metrics_text.append(f"  Std: {spread_stats.get('std', 0):.5f}")

        # Display as text
        text_str = "\n".join(metrics_text)
        ax.text(
            0.1,
            0.9,
            text_str,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            family="monospace",
        )
        ax.set_title("Detailed Metrics", fontsize=12, fontweight="bold")

    # ==================== Heatmap Generation ====================

    def generate_completeness_heatmap(
        self, data: pd.DataFrame, segments: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Generate continuity heatmap data by dividing timeline into segments.

        Args:
            data: DataFrame with datetime index or time column
            segments: Number of segments to divide the timeline into

        Returns:
            List of segment info dicts with status, date, range
        """
        time_series = self._get_time_series(data)
        if time_series is None or len(time_series) < 2:
            return []

        start_time = time_series.min()
        end_time = time_series.max()
        total_duration = end_time - start_time
        segment_duration = total_duration / segments

        heatmap_data = []

        # Convert to dataframe for easier filtering
        df_times = pd.DataFrame({"time": time_series})

        # Calculate expected count per segment roughly (assuming uniform distribution)
        # Better approach: check max gap size in segment

        for i in range(segments):
            seg_start = start_time + (segment_duration * i)
            seg_end = seg_start + segment_duration

            # Filter data in this segment
            # Using searchsorted for speed if sorted?
            # Or just boolean mask for simplicity first
            mask = (df_times["time"] >= seg_start) & (df_times["time"] < seg_end)
            seg_data = df_times[mask]

            status = "ok"

            if seg_data.empty:
                status = "gap"  # Completely empty segment
            else:
                # Check for internal gaps if we want to be strict
                # For heatmap, maybe just existence is enough or coverage?
                # Let's say if we have less than 10% of expected points?
                # But we don't know expected freq for sure.
                # Let's stick to "empty" or "max gap > threshold"

                # Let's use the max gap check if we have enough points
                if len(seg_data) > 1:
                    diffs = seg_data["time"].diff().max()
                    # If max gap is > 20% of segment duration, flag it
                    if diffs > segment_duration * 0.2:
                        status = "gap"

            heatmap_data.append(
                {
                    "index": i,
                    "status": status,
                    "date": seg_start.strftime("%Y-%m-%d"),
                    "range": f"{seg_start.strftime('%H:%M')} - {seg_end.strftime('%H:%M')}",
                    "start_iso": seg_start.isoformat(),
                    "end_iso": seg_end.isoformat(),
                }
            )

        return heatmap_data


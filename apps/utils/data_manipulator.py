"""
Data Manipulator - Timeframe Management and Bar Aggregation.

This module provides data manipulation utilities including:
- TimeframeManager: Resampling and timeframe conversions
- BarAggregator: Incremental bar aggregation for live trading
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from apps.logger import logger


class TimeframeManager:
    """
    Manager for OHLCV data resampling and timeframe conversions.

    Provides methods for:
    - Resampling OHLCV data between timeframes
    - Converting timeframe strings to pandas frequencies
    - Incremental bar aggregation for live trading
    - Multi-timeframe resolution
    """

    # Timeframe to pandas frequency mapping
    TIMEFRAME_MAP: Dict[str, str] = {
        "M1": "1min",  # 1 minute
        "M5": "5min",  # 5 minutes
        "M15": "15min",  # 15 minutes
        "M30": "30min",  # 30 minutes
        "H1": "1h",  # 1 hour
        "H4": "4h",  # 4 hours
        "D1": "1D",  # 1 day
        "W1": "1W",  # 1 week
        "MN1": "1M",  # 1 month
    }

    # Valid timeframes in order of granularity
    VALID_TIMEFRAMES: List[str] = [
        "M1",
        "M5",
        "M15",
        "M30",
        "H1",
        "H4",
        "D1",
        "W1",
        "MN1",
    ]

    def __init__(self):
        """Initialize TimeframeManager."""
        logger.debug("TimeframeManager initialized")

    @classmethod
    def timeframe_to_frequency(cls, timeframe: str) -> str:
        """
        Convert timeframe string to pandas frequency string.

        Args:
            timeframe: Timeframe string (e.g., 'M1', 'H1', 'D1')

        Returns:
            Pandas frequency string (e.g., '1T', '1H', '1D')

        Raises:
            ValueError: If timeframe is not supported

        Examples:
            >>> TimeframeManager.timeframe_to_frequency('M1')
            '1T'
            >>> TimeframeManager.timeframe_to_frequency('H1')
            '1H'
            >>> TimeframeManager.timeframe_to_frequency('D1')
            '1D'
        """
        timeframe_upper = timeframe.upper()
        if timeframe_upper not in cls.TIMEFRAME_MAP:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. "
                f"Supported timeframes: {', '.join(cls.VALID_TIMEFRAMES)}"
            )
        return cls.TIMEFRAME_MAP[timeframe_upper]

    @classmethod
    def validate_timeframe(cls, timeframe: str) -> bool:
        """
        Validate if timeframe string is supported.

        Args:
            timeframe: Timeframe string to validate

        Returns:
            True if valid, False otherwise
        """
        return timeframe.upper() in cls.TIMEFRAME_MAP

    @classmethod
    def can_resample(cls, from_timeframe: str, to_timeframe: str) -> bool:
        """
        Check if resampling from one timeframe to another is possible.

        Resampling is only possible if target timeframe is larger (less granular)
        than source timeframe.

        Args:
            from_timeframe: Source timeframe
            to_timeframe: Target timeframe

        Returns:
            True if resampling is possible, False otherwise
        """
        try:
            from_idx = cls.VALID_TIMEFRAMES.index(from_timeframe.upper())
            to_idx = cls.VALID_TIMEFRAMES.index(to_timeframe.upper())
            return to_idx > from_idx
        except ValueError:
            return False

    def _find_ohlcv_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Find OHLCV columns in DataFrame (case-insensitive).

        Args:
            df: DataFrame to search

        Returns:
            Dictionary mapping standard names to actual column names
        """
        mapping = {}
        columns_lower = {col.lower(): col for col in df.columns}

        # Map standard OHLCV column names
        ohlcv_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }

        for key, standard_name in ohlcv_map.items():
            if key in columns_lower:
                mapping[standard_name] = columns_lower[key]

        return mapping

    def _ensure_datetime_index(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure DataFrame has DatetimeIndex.

        Args:
            data: DataFrame to process

        Returns:
            DataFrame with DatetimeIndex

        Raises:
            ValueError: If no datetime column found
        """
        if isinstance(data.index, pd.DatetimeIndex):
            return data

        # Try to find datetime column
        datetime_cols = [
            "Datetime",
            "datetime",
            "time",
            "Time",
            "timestamp",
            "Timestamp",
        ]
        datetime_col = None
        for col in datetime_cols:
            if col in data.columns:
                datetime_col = col
                break

        if datetime_col:
            data = data.copy()
            data.index = pd.DatetimeIndex(data[datetime_col], name="Datetime")
            data = data.drop(columns=[datetime_col])
            return data

        raise ValueError(
            "DataFrame must have DatetimeIndex or a datetime column "
            "(Datetime, datetime, time, timestamp)"
        )

    def _resample_ohlcv_columns(
        self, data: pd.DataFrame, ohlcv_mapping: Dict[str, str], frequency: str
    ) -> pd.DataFrame:
        """
        Resample OHLCV columns according to standard rules.

        Args:
            data: DataFrame with OHLCV data
            ohlcv_mapping: Mapping of standard names to actual column names
            frequency: Pandas frequency string

        Returns:
            DataFrame with resampled OHLCV columns
        """
        resampled = pd.DataFrame(index=data.index)

        # Open: first value in period
        if "Open" in ohlcv_mapping:
            resampled["Open"] = data[ohlcv_mapping["Open"]].resample(frequency).first()

        # High: maximum value in period
        if "High" in ohlcv_mapping:
            resampled["High"] = data[ohlcv_mapping["High"]].resample(frequency).max()

        # Low: minimum value in period
        if "Low" in ohlcv_mapping:
            resampled["Low"] = data[ohlcv_mapping["Low"]].resample(frequency).min()

        # Close: last value in period
        if "Close" in ohlcv_mapping:
            resampled["Close"] = data[ohlcv_mapping["Close"]].resample(frequency).last()

        # Volume: sum of volumes in period
        if "Volume" in ohlcv_mapping:
            resampled["Volume"] = (
                data[ohlcv_mapping["Volume"]].resample(frequency).sum()
            )

        return resampled

    def _resample_other_columns(
        self, data: pd.DataFrame, ohlcv_mapping: Dict[str, str], frequency: str
    ) -> pd.DataFrame:
        """
        Resample non-OHLCV columns (use last value).

        Args:
            data: DataFrame with data
            ohlcv_mapping: Mapping of standard names to actual column names
            frequency: Pandas frequency string

        Returns:
            DataFrame with resampled other columns
        """
        resampled = pd.DataFrame(index=data.index)

        # Copy other columns if they exist (e.g., Spread)
        other_cols = [
            col
            for col in data.columns
            if col not in ohlcv_mapping.values() and col not in ["Datetime", "datetime"]
        ]
        for col in other_cols:
            # For other columns, use last value
            resampled[col] = data[col].resample(frequency).last()

        return resampled

    def resample(
        self,
        data: pd.DataFrame,
        target_timeframe: str,
        source_timeframe: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Resample OHLCV data to a different timeframe.

        Args:
            data: DataFrame with OHLCV data (must have DatetimeIndex)
            target_timeframe: Target timeframe string (e.g., 'M5', 'H1', 'D1')
            source_timeframe: Optional source timeframe for validation

        Returns:
            Resampled DataFrame with same column structure

        Raises:
            ValueError: If data doesn't have DatetimeIndex or timeframe is invalid
            ValueError: If resampling is not possible (target smaller than source)

        Examples:
            >>> manager = TimeframeManager()
            >>> # Resample M1 data to M5
            >>> m5_data = manager.resample(m1_data, 'M5')
            >>> # Resample M5 data to H1
            >>> h1_data = manager.resample(m5_data, 'H1')
        """
        if data.empty:
            logger.warning("Cannot resample empty DataFrame")
            return data.copy()

        # Validate target timeframe
        if not self.validate_timeframe(target_timeframe):
            raise ValueError(
                f"Invalid target timeframe: {target_timeframe}. "
                f"Supported: {', '.join(self.VALID_TIMEFRAMES)}"
            )

        # Check if resampling is possible
        if source_timeframe and not self.can_resample(
            source_timeframe, target_timeframe
        ):
            raise ValueError(
                f"Cannot resample from {source_timeframe} to {target_timeframe}. "
                f"Target timeframe must be larger (less granular)."
            )

        # Ensure DatetimeIndex
        data = self._ensure_datetime_index(data)

        # Find OHLCV columns
        ohlcv_mapping = self._find_ohlcv_columns(data)
        if not ohlcv_mapping:
            raise ValueError("No OHLCV columns found in DataFrame")

        # Convert timeframe to pandas frequency
        frequency = self.timeframe_to_frequency(target_timeframe)

        # Resample OHLCV columns
        resampled = self._resample_ohlcv_columns(data, ohlcv_mapping, frequency)

        # Resample other columns and add to resampled DataFrame
        other_cols = [
            col
            for col in data.columns
            if col not in ohlcv_mapping.values() and col not in ["Datetime", "datetime"]
        ]
        for col in other_cols:
            # For other columns, use last value
            resampled[col] = data[col].resample(frequency).last()

        # Remove rows where all OHLCV values are NaN
        resampled = resampled.dropna(subset=["Open", "High", "Low", "Close"], how="all")

        logger.info(
            f"Resampled {len(data):,} rows to {target_timeframe}: "
            f"{len(resampled):,} rows"
        )

        return resampled

    def resample_multi_timeframe(
        self,
        data: pd.DataFrame,
        source_timeframe: str,
        target_timeframes: List[str],
    ) -> Dict[str, pd.DataFrame]:
        """
        Resample data to multiple target timeframes.

        Args:
            data: DataFrame with OHLCV data
            source_timeframe: Source timeframe string
            target_timeframes: List of target timeframe strings

        Returns:
            Dictionary mapping timeframe strings to resampled DataFrames

        Examples:
            >>> manager = TimeframeManager()
            >>> results = manager.resample_multi_timeframe(m1_data, 'M1', ['M5', 'H1', 'D1'])
            >>> m5_data = results['M5']
            >>> h1_data = results['H1']
        """
        results = {}
        for target_tf in target_timeframes:
            try:
                resampled = self.resample(data, target_tf, source_timeframe)
                results[target_tf] = resampled
                results[target_tf].name = target_tf
                logger.debug(f"Resampled to {target_tf}: {len(resampled):,} rows")
            except ValueError as e:
                logger.warning(f"Failed to resample to {target_tf}: {e}")
                continue

        return results


class BarAggregator:
    """
    Incremental bar aggregator for live trading.

    Aggregates ticks or smaller timeframe bars into larger timeframe bars
    incrementally, suitable for real-time trading scenarios.
    """

    def __init__(self, target_timeframe: str):
        """
        Initialize bar aggregator.

        Args:
            target_timeframe: Target timeframe for aggregated bars (e.g., 'M5', 'H1')
        """
        self.target_timeframe = target_timeframe.upper()
        self.target_frequency = TimeframeManager.timeframe_to_frequency(
            target_timeframe
        )

        # Current bar being built
        self.current_bar: Optional[Dict[str, float]] = None
        self.current_bar_start: Optional[datetime] = None

        # Completed bars
        self.completed_bars: List[Dict[str, Any]] = []

        logger.debug(f"BarAggregator initialized for {target_timeframe}")

    def add_tick(
        self,
        timestamp: datetime,
        price: float,
        volume: float = 0.0,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Add a tick to the current bar and return completed bar if period ended.

        Args:
            timestamp: Tick timestamp
            price: Price (or mid-price if bid/ask provided)
            volume: Volume (default: 0.0)
            bid: Bid price (optional)
            ask: Ask price (optional)

        Returns:
            Completed bar dictionary if period ended, None otherwise
        """
        # Use mid-price if bid/ask provided
        if bid is not None and ask is not None:
            price = (bid + ask) / 2.0

        # Normalize timestamp to bar start time
        bar_start = self._get_bar_start_time(timestamp)

        # If new bar period started, finalize previous bar
        completed_bar = None
        if self.current_bar_start is not None and bar_start != self.current_bar_start:
            completed_bar = self._finalize_current_bar()
            self.completed_bars.append(completed_bar)

        # Initialize new bar if needed
        if bar_start != self.current_bar_start:
            self.current_bar_start = bar_start
            self.current_bar = {
                "Open": price,
                "High": price,
                "Low": price,
                "Close": price,
                "Volume": volume,
            }
        else:
            # Update current bar
            if self.current_bar:
                self.current_bar["High"] = max(self.current_bar["High"], price)
                self.current_bar["Low"] = min(self.current_bar["Low"], price)
                self.current_bar["Close"] = price
                self.current_bar["Volume"] += volume

        return completed_bar

    def add_bar(
        self,
        timestamp: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Add a smaller timeframe bar to aggregate into larger bar.

        Args:
            timestamp: Bar timestamp
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Volume

        Returns:
            Completed bar dictionary if period ended, None otherwise
        """
        # Normalize timestamp to bar start time
        bar_start = self._get_bar_start_time(timestamp)

        # If new bar period started, finalize previous bar
        completed_bar = None
        if self.current_bar_start is not None and bar_start != self.current_bar_start:
            completed_bar = self._finalize_current_bar()
            self.completed_bars.append(completed_bar)

        # Initialize new bar if needed
        if bar_start != self.current_bar_start:
            self.current_bar_start = bar_start
            self.current_bar = {
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
                "Volume": volume,
            }
        else:
            # Update current bar with new bar data
            if self.current_bar:
                self.current_bar["High"] = max(self.current_bar["High"], high_price)
                self.current_bar["Low"] = min(self.current_bar["Low"], low_price)
                self.current_bar["Close"] = close_price
                self.current_bar["Volume"] += volume

        return completed_bar

    def _get_bar_start_time(self, timestamp: datetime) -> datetime:
        """
        Get the start time of the bar period for given timestamp.

        Args:
            timestamp: Timestamp to normalize

        Returns:
            Bar start timestamp
        """
        # Convert to pandas Timestamp for resample
        ts = pd.Timestamp(timestamp)
        # Resample to get period start
        period = pd.Period(ts, freq=self.target_frequency)
        result: datetime = period.start_time.to_pydatetime()
        return result

    def _finalize_current_bar(self) -> Dict[str, Any]:
        """
        Finalize current bar and return it.

        Returns:
            Completed bar dictionary with timestamp
        """
        if not self.current_bar or self.current_bar_start is None:
            raise ValueError("No current bar to finalize")

        # Type narrowing: we know current_bar is not None after the check
        bar: Dict[str, Any] = dict(self.current_bar)
        bar["Datetime"] = self.current_bar_start
        return bar

    def get_current_bar(self) -> Optional[Dict[str, Any]]:
        """
        Get current incomplete bar.

        Returns:
            Current bar dictionary with timestamp, or None if no bar in progress
        """
        if not self.current_bar or self.current_bar_start is None:
            return None

        # Type narrowing: we know current_bar is not None after the check
        bar: Dict[str, Any] = dict(self.current_bar)
        bar["Datetime"] = self.current_bar_start
        return bar

    def get_completed_bars(self) -> List[Dict[str, Any]]:
        """
        Get all completed bars.

        Returns:
            List of completed bar dictionaries
        """
        return self.completed_bars.copy()

    def flush(self) -> Optional[Dict[str, Any]]:
        """
        Flush current incomplete bar as completed.

        Returns:
            Flushed bar dictionary, or None if no bar in progress
        """
        if not self.current_bar or self.current_bar_start is None:
            return None

        completed_bar = self._finalize_current_bar()
        self.completed_bars.append(completed_bar)
        self.current_bar = None
        self.current_bar_start = None

        return completed_bar


def create_signal_mapping(
    trading_tf_data: pd.DataFrame,
    m1_data: pd.DataFrame,
) -> Dict[pd.Timestamp, Dict[str, float]]:
    """
    Create mapping from M1 timestamps to trading timeframe signals.

    This function maps each M1 bar to the signals from its corresponding
    trading timeframe bar (e.g., H1, H4, D1). Maintains the "shift by 1 bar"
    behavior where signals from bar T execute at bar T+1.

    Args:
        trading_tf_data: DataFrame with signals on trading timeframe (e.g., H1)
                        Must have columns: EntrySignal, ExitSignal
                        Optional columns: SL, TP
        m1_data: DataFrame with M1 bars

    Returns:
        Dictionary mapping M1 timestamps to signal dictionaries:
        {
            m1_timestamp: {
                "EntrySignal": float,
                "ExitSignal": float,
                "SL": float,
                "TP": float
            }
        }

    Example:
        >>> # H1 signal at 10:00 executes at 11:00 H1 bar
        >>> # In M1 mode, executes at first M1 bar of 11:00 (11:00:00)
        >>> signal_map = create_signal_mapping(h1_data, m1_data)
        >>> # M1 bars from 11:00:00 to 11:59:00 all map to the same H1 signals
    """
    signal_map: Dict[pd.Timestamp, Dict[str, float]] = {}

    # Ensure both DataFrames have DatetimeIndex
    if not isinstance(trading_tf_data.index, pd.DatetimeIndex):
        raise ValueError("trading_tf_data must have DatetimeIndex")
    if not isinstance(m1_data.index, pd.DatetimeIndex):
        raise ValueError("m1_data must have DatetimeIndex")

    # Get required signal columns
    required_cols = ["EntrySignal", "ExitSignal"]
    for col in required_cols:
        if col not in trading_tf_data.columns:
            raise ValueError(f"trading_tf_data missing required column: {col}")

    # Check for optional columns
    has_sl = "SL" in trading_tf_data.columns
    has_tp = "TP" in trading_tf_data.columns

    logger.debug(
        f"Creating signal mapping: {len(trading_tf_data)} trading TF bars -> "
        f"{len(m1_data)} M1 bars"
    )

    # Infer trading timeframe from data frequency
    # Calculate median time delta between bars
    if len(trading_tf_data) > 1:
        time_deltas = trading_tf_data.index.to_series().diff().dropna()
        median_delta = time_deltas.median()
        tf_minutes = int(median_delta.total_seconds() / 60)
    else:
        # Default to H1 if can't infer
        tf_minutes = 60
        logger.warning("Cannot infer trading timeframe, assuming H1 (60 minutes)")

    logger.debug(f"Inferred trading timeframe: {tf_minutes} minutes")

    # Create mapping for each M1 bar
    for m1_timestamp in m1_data.index:
        # Find the trading TF bar that this M1 bar belongs to
        # Floor to the trading timeframe interval
        trading_tf_timestamp = m1_timestamp.floor(f"{tf_minutes}min")

        # Look up signals from the trading TF bar
        if trading_tf_timestamp in trading_tf_data.index:
            signal_map[m1_timestamp] = {
                "EntrySignal": float(
                    cast(Any, trading_tf_data.loc[trading_tf_timestamp, "EntrySignal"])
                ),
                "ExitSignal": float(
                    cast(Any, trading_tf_data.loc[trading_tf_timestamp, "ExitSignal"])
                ),
                "SL": (
                    float(cast(Any, trading_tf_data.loc[trading_tf_timestamp, "SL"]))
                    if has_sl
                    else 0.0
                ),
                "TP": (
                    float(cast(Any, trading_tf_data.loc[trading_tf_timestamp, "TP"]))
                    if has_tp
                    else 0.0
                ),
            }
        else:
            # No trading TF bar for this M1 bar (shouldn't happen if data is aligned)
            signal_map[m1_timestamp] = {
                "EntrySignal": 0.0,
                "ExitSignal": 0.0,
                "SL": 0.0,
                "TP": 0.0,
            }

    logger.success(
        f"Signal mapping created: {len(signal_map)} M1 bars mapped to trading TF signals"
    )

    return signal_map

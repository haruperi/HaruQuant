"""
Data Manipulator - Timeframe Management and Bar Aggregation.

This module provides data manipulation utilities including:
- TimeframeManager: Resampling and timeframe conversions
- BarAggregator: Incremental bar aggregation for live trading
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast
import random

import numpy as np
import pandas as pd

from backend.common.logger import logger


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


class TicksGenerator:
    """Generate tick DataFrames from different source models.
    Source used for synthetic_ticks: https://www.mql5.com/en/articles/75.
    """

    SUPPORTED_MODELS = {"timeframe_ticks", "m1_ticks", "real_ticks", "synthetic_ticks"}

    def __init__(
        self,
        model: str,
        trading_timeframe: str,
        m1_data: Optional[pd.DataFrame] = None,
        real_ticks: Optional[pd.DataFrame] = None,
        point_value: float = 0.00001,
        spread_model: str = "native_spread",
        fixed_spread_points: Optional[float] = None,
        min_spread_points: Optional[float] = None,
        max_spread_points: Optional[float] = None,
        random_seed: Optional[int] = None,
    ):
        self.model = str(model).lower()
        self.trading_timeframe = trading_timeframe.upper()
        self.m1_data = m1_data
        self.real_ticks = real_ticks
        self.point_value = float(point_value)
        self.spread_model = str(spread_model).lower()
        self.fixed_spread_points = fixed_spread_points
        self.min_spread_points = min_spread_points
        self.max_spread_points = max_spread_points
        self._rng = random.Random(random_seed)

        if self.model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported ticks model: {model}. "
                f"Supported models: {sorted(self.SUPPORTED_MODELS)}"
            )
        if self.point_value <= 0.0:
            raise ValueError("point_value must be > 0")
        valid_spread_models = {"native_spread", "fixed_spread", "variable_spread"}
        if self.spread_model not in valid_spread_models:
            raise ValueError(
                f"Unsupported spread_model: {spread_model}. "
                f"Supported: {sorted(valid_spread_models)}"
            )
        if self.spread_model == "fixed_spread":
            if self.fixed_spread_points is None:
                raise ValueError("fixed_spread_points is required for fixed_spread model.")
            if float(self.fixed_spread_points) < 0.0:
                raise ValueError("fixed_spread_points must be >= 0.")
        if self.spread_model == "variable_spread":
            if self.min_spread_points is None or self.max_spread_points is None:
                raise ValueError(
                    "min_spread_points and max_spread_points are required for variable_spread model."
                )
            if float(self.min_spread_points) < 0.0 or float(self.max_spread_points) < 0.0:
                raise ValueError("min_spread_points and max_spread_points must be >= 0.")
            if float(self.min_spread_points) > float(self.max_spread_points):
                raise ValueError("min_spread_points cannot be greater than max_spread_points.")

    def generate(self, trading_tf_data: pd.DataFrame) -> pd.DataFrame:
        """Generate a standardized tick DataFrame."""
        if self.model == "timeframe_ticks":
            return self._generate_timeframe_ticks(trading_tf_data)
        if self.model == "m1_ticks":
            return self._generate_m1_ticks(trading_tf_data)
        if self.model == "real_ticks":
            return self._generate_real_ticks(trading_tf_data)
        if self.model == "synthetic_ticks":
            return self._generate_synthetic_ticks(trading_tf_data)
        raise ValueError(f"Unsupported model: {self.model}")

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        lower = {str(c).lower(): str(c) for c in df.columns}
        for name in candidates:
            if name.lower() in lower:
                return lower[name.lower()]
        return None

    @staticmethod
    def _infer_bar_seconds(index: pd.DatetimeIndex) -> int:
        if len(index) > 1:
            deltas = index.to_series().diff().dropna()
            if not deltas.empty:
                secs = int(max(1, deltas.median().total_seconds()))
                return secs
        return 60

    def _generate_timeframe_ticks(self, bars: pd.DataFrame) -> pd.DataFrame:
        if bars is None or bars.empty:
            return pd.DataFrame(
                columns=[
                    "bid",
                    "ask",
                    "last",
                    "spread",
                    "entry_signal",
                    "exit_signal",
                    "pending_signal",
                    "cancel_pending_signal",
                    "pending_signal_2",
                    "cancel_pending_signal_2",
                    "price",
                    "price_2",
                    "sl",
                    "tp",
                    "source_bar_time",
                    "tick_index_in_bar",
                    "is_bar_close",
                ]
            )

        if not isinstance(bars.index, pd.DatetimeIndex):
            manager = TimeframeManager()
            bars = manager._ensure_datetime_index(bars)

        open_col = self._find_col(bars, ["Open"])
        high_col = self._find_col(bars, ["High"])
        low_col = self._find_col(bars, ["Low"])
        close_col = self._find_col(bars, ["Close"])
        spread_col = self._find_col(bars, ["Spread"])
        entry_col = self._find_col(bars, ["entry_signal"])
        exit_col = self._find_col(bars, ["exit_signal"])
        pending_col = self._find_col(bars, ["pending_signal"])
        cancel_pending_col = self._find_col(bars, ["cancel_pending_signal"])
        pending_col_2 = self._find_col(bars, ["pending_signal_2"])
        cancel_pending_col_2 = self._find_col(bars, ["cancel_pending_signal_2"])
        price_col = self._find_col(bars, ["price"])
        price_col_2 = self._find_col(bars, ["price_2"])
        sl_col = self._find_col(bars, ["sl"])
        tp_col = self._find_col(bars, ["tp"])

        required = [open_col, high_col, low_col, close_col]
        if any(col is None for col in required):
            raise ValueError(
                "timeframe_ticks requires OHLC columns: Open, High, Low, Close"
            )

        n_bars = len(bars.index)
        if n_bars == 0:
            return pd.DataFrame(
                columns=[
                    "bid",
                    "ask",
                    "last",
                    "spread",
                    "entry_signal",
                    "exit_signal",
                    "pending_signal",
                    "cancel_pending_signal",
                    "sl",
                    "tp",
                    "source_bar_time",
                    "tick_index_in_bar",
                    "is_bar_close",
                ]
            )

        def _bar_col_or_zeros(col_name: Optional[str]) -> np.ndarray:
            if col_name is None:
                return np.zeros(n_bars, dtype=np.float64)
            values = pd.to_numeric(bars[cast(str, col_name)], errors="coerce").to_numpy(
                dtype=np.float64,
                copy=False,
            )
            # Match prior behavior where NaN in signals/spread became 0.0.
            return np.nan_to_num(values, nan=0.0)

        open_arr = _bar_col_or_zeros(open_col)
        high_arr = _bar_col_or_zeros(high_col)
        low_arr = _bar_col_or_zeros(low_col)
        close_arr = _bar_col_or_zeros(close_col)
        native_spread_arr = _bar_col_or_zeros(spread_col)
        entry_arr = _bar_col_or_zeros(entry_col)
        exit_arr = _bar_col_or_zeros(exit_col)
        pending_arr = _bar_col_or_zeros(pending_col)
        cancel_pending_arr = _bar_col_or_zeros(cancel_pending_col)
        pending_arr_2 = _bar_col_or_zeros(pending_col_2)
        cancel_pending_arr_2 = _bar_col_or_zeros(cancel_pending_col_2)
        price_arr = _bar_col_or_zeros(price_col)
        price_arr_2 = _bar_col_or_zeros(price_col_2)
        sl_arr = _bar_col_or_zeros(sl_col)
        tp_arr = _bar_col_or_zeros(tp_col)

        bar_seconds = self._infer_bar_seconds(bars.index)
        offsets_ms = np.array(
            [0, int(bar_seconds * 250), int(bar_seconds * 500), int(bar_seconds * 750)],
            dtype=np.int64,
        )

        # 4-tick bar path: bullish O-L-H-C, bearish O-H-L-C
        bullish = close_arr >= open_arr
        total_ticks = n_bars * 4
        bid = np.empty(total_ticks, dtype=np.float64)
        bid[0::4] = open_arr
        bid[1::4] = np.where(bullish, low_arr, high_arr)
        bid[2::4] = np.where(bullish, high_arr, low_arr)
        bid[3::4] = close_arr

        # is_bar_close: True only for the 4th tick of every bar
        is_bar_close = np.zeros(total_ticks, dtype=bool)
        is_bar_close[3::4] = True

        if self.spread_model == "native_spread":
            spread_points = np.repeat(np.maximum(native_spread_arr, 0.0), 4)
        elif self.spread_model == "fixed_spread":
            fixed = max(0.0, float(self.fixed_spread_points or 0.0))
            spread_points = np.full(total_ticks, fixed, dtype=np.float64)
        else:
            low = float(self.min_spread_points or 0.0)
            high = float(self.max_spread_points or 0.0)
            spread_points = np.array(
                [max(0.0, self._rng.uniform(low, high)) for _ in range(total_ticks)],
                dtype=np.float64,
            )

        ask = bid + (spread_points * self.point_value)
        spread_int = np.rint(np.maximum(spread_points, 0.0)).astype(np.int64)

        entry_signal = np.zeros(total_ticks, dtype=np.float64)
        exit_signal = np.zeros(total_ticks, dtype=np.float64)
        pending_signal = np.zeros(total_ticks, dtype=np.float64)
        cancel_pending_signal = np.zeros(total_ticks, dtype=np.float64)
        pending_signal_2 = np.zeros(total_ticks, dtype=np.float64)
        cancel_pending_signal_2 = np.zeros(total_ticks, dtype=np.float64)
        price = np.zeros(total_ticks, dtype=np.float64)
        price_2 = np.zeros(total_ticks, dtype=np.float64)
        sl = np.zeros(total_ticks, dtype=np.float64)
        tp = np.zeros(total_ticks, dtype=np.float64)
        entry_signal[0::4] = entry_arr
        exit_signal[0::4] = exit_arr
        pending_signal[0::4] = pending_arr
        cancel_pending_signal[0::4] = cancel_pending_arr
        pending_signal_2[0::4] = pending_arr_2
        cancel_pending_signal_2[0::4] = cancel_pending_arr_2
        price[0::4] = price_arr
        price_2[0::4] = price_arr_2
        sl[0::4] = sl_arr
        tp[0::4] = tp_arr

        bar_times = bars.index.to_numpy(dtype="datetime64[ns]")
        tick_times = (
            np.repeat(bar_times.astype("int64"), 4)
            + np.tile(offsets_ms * 1_000_000, n_bars)
        )
        datetime_index = pd.DatetimeIndex(
            pd.to_datetime(tick_times),
            name="Datetime",
        )

        ticks = pd.DataFrame(
            {
                "bid": bid,
                "ask": ask,
                "last": bid,
                "spread": spread_int,
                "entry_signal": entry_signal,
                "exit_signal": exit_signal,
                "pending_signal": pending_signal,
                "cancel_pending_signal": cancel_pending_signal,
                "pending_signal_2": pending_signal_2,
                "cancel_pending_signal_2": cancel_pending_signal_2,
                "price": price,
                "price_2": price_2,
                "sl": sl,
                "tp": tp,
                "source_bar_time": np.repeat(bar_times, 4),
                "tick_index_in_bar": np.tile(np.array([0, 1, 2, 3], dtype=np.int64), n_bars),
                "is_bar_close": is_bar_close,
            },
            index=datetime_index,
        )
        ticks = ticks.sort_index()
        return ticks

    def _resolve_spread_points(self, native_spread_points: float) -> float:
        """Resolve spread in points according to configured spread model."""
        if self.spread_model == "native_spread":
            return float(max(0.0, native_spread_points))
        if self.spread_model == "fixed_spread":
            return float(max(0.0, float(self.fixed_spread_points or 0.0)))
        # variable_spread
        low = float(self.min_spread_points or 0.0)
        high = float(self.max_spread_points or 0.0)
        return float(max(0.0, self._rng.uniform(low, high)))

    @staticmethod
    def _spread_points_to_int(spread_points: float) -> int:
        return int(round(max(0.0, float(spread_points))))

    @staticmethod
    def _ensure_signal_columns(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for col in (
            "entry_signal",
            "exit_signal",
            "pending_signal",
            "cancel_pending_signal",
            "pending_signal_2",
            "cancel_pending_signal_2",
            "price",
            "price_2",
            "sl",
            "tp",
        ):
            if col not in out.columns:
                out[col] = 0.0
        return out

    def _prepare_m1_with_signals(self, trading_tf_data: pd.DataFrame) -> pd.DataFrame:
        if self.m1_data is None or self.m1_data.empty:
            raise ValueError("m1_ticks/synthetic_ticks requires non-empty m1_data.")

        manager = TimeframeManager()
        trading_tf = trading_tf_data
        m1 = self.m1_data.copy()
        if not isinstance(trading_tf.index, pd.DatetimeIndex):
            trading_tf = manager._ensure_datetime_index(trading_tf)
        if not isinstance(m1.index, pd.DatetimeIndex):
            m1 = manager._ensure_datetime_index(m1)

        # 1. Isolate and normalize signal columns
        expected_cols = (
            "entry_signal", "exit_signal", "pending_signal", "cancel_pending_signal",
            "pending_signal_2", "cancel_pending_signal_2", "price", "price_2", "sl", "tp"
        )
        trading_tf = self._ensure_signal_columns(trading_tf)
        tf_signals = trading_tf[list(expected_cols)].copy()

        # 2. Vectorized Mapping:
        # Infer timeframe of trading signals to know the 'floor' boundary
        tf_seconds = self._infer_bar_seconds(trading_tf.index)
        
        # Floor M1 index to the boundary of the trading timeframe
        # e.g. 10:23:00 -> 10:00:00 for H1
        floored_index = m1.index.floor(f"{max(1, tf_seconds)}s")
        
        # Ensure tf_signals index is also floored for perfect alignment
        tf_signals.index = tf_signals.index.floor(f"{max(1, tf_seconds)}s")
        
        # Broadcast signals to M1 bars instantly using reindex
        # This replaces the O(N*M) dictionary lookup and O(N) .at loop
        mapped_signals = tf_signals.reindex(floored_index).fillna(0.0)
        
        # Restore precise M1 timestamps
        mapped_signals.index = m1.index
        
        # Assign all mapped columns to m1 in one go
        for col in expected_cols:
            m1[col] = mapped_signals[col]

        logger.success(f"Vectorized signal mapping complete: {len(m1)} bars mapped.")
        return m1

    def _generate_m1_ticks(self, trading_tf_data: pd.DataFrame) -> pd.DataFrame:
        """Merge trading timeframe signals into M1 bars and generate 4 ticks/bar."""
        m1_with_signals = self._prepare_m1_with_signals(trading_tf_data)
        return self._generate_timeframe_ticks(m1_with_signals)

    def _generate_real_ticks(self, trading_tf_data: pd.DataFrame) -> pd.DataFrame:
        """Merge trading timeframe signals into real ticks."""
        if self.real_ticks is None or self.real_ticks.empty:
            raise ValueError("real_ticks model requires non-empty real_ticks DataFrame.")

        manager = TimeframeManager()
        ticks = self.real_ticks.copy()
        tf = trading_tf_data.copy()
        if not isinstance(ticks.index, pd.DatetimeIndex):
            ticks = manager._ensure_datetime_index(ticks)
        if not isinstance(tf.index, pd.DatetimeIndex):
            tf = manager._ensure_datetime_index(tf)
        tf = self._ensure_signal_columns(tf)

        bid_col = self._find_col(ticks, ["bid"])
        ask_col = self._find_col(ticks, ["ask"])
        if bid_col is None or ask_col is None:
            raise ValueError("real_ticks DataFrame must contain bid and ask columns.")
        last_col = self._find_col(ticks, ["last"])
        volume_col = self._find_col(ticks, ["volume", "tick_volume"])
        spread_col = self._find_col(ticks, ["spread"])

        tf_seconds = self._infer_bar_seconds(tf.index)
        bucket = ticks.index.floor(f"{max(1, tf_seconds)}s")
        first_in_bucket = ~bucket.duplicated()

        signal_cols = [
            "entry_signal",
            "exit_signal",
            "pending_signal",
            "cancel_pending_signal",
            "sl",
            "tp",
        ]
        tf_signal = tf[signal_cols].copy()
        tf_signal.index = tf_signal.index.floor(f"{max(1, tf_seconds)}s")
        merged_signal = tf_signal.reindex(bucket).fillna(0.0).reset_index(drop=True)

        out = pd.DataFrame(index=ticks.index)
        out["bid"] = ticks[bid_col].astype(float)
        out["ask"] = ticks[ask_col].astype(float)
        out["last"] = (
            ticks[last_col].astype(float) if last_col is not None else out["bid"]
        )
        out["spread"] = (
            ticks[spread_col].astype(float)
            if spread_col is not None
            else (out["ask"] - out["bid"]) / self.point_value
        )

        for col in signal_cols:
            values = merged_signal[col].to_numpy()
            out[col] = values
            out.loc[~first_in_bucket, col] = 0.0

        out["source_bar_time"] = bucket
        out["tick_index_in_bar"] = pd.Series(bucket, index=out.index).groupby(bucket).cumcount()
        
        # is_bar_close: True for the last tick in each bucket
        out["is_bar_close"] = ~bucket.duplicated(keep="last")
        
        out.index = pd.DatetimeIndex(out.index, name="Datetime")
        return out.sort_index()

    @staticmethod
    def _interpolate_path(path: List[float], n: int) -> List[float]:
        if n <= 1:
            return [float(path[0])]
        if len(path) < 2:
            return [float(path[0])] * n

        segments = len(path) - 1
        total_steps = n - 1
        base = total_steps // segments
        rem = total_steps % segments
        ticks = [float(path[0])]
        for i in range(segments):
            p0 = float(path[i])
            p1 = float(path[i + 1])
            steps = base + (1 if i < rem else 0)
            if steps <= 0:
                continue
            for s in range(1, steps + 1):
                ratio = float(s) / float(steps)
                ticks.append(p0 + ((p1 - p0) * ratio))
        if len(ticks) > n:
            ticks = ticks[:n]
        while len(ticks) < n:
            ticks.append(float(path[-1]))
        return ticks

    def _generate_synthetic_ticks(self, trading_tf_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate synthetic ticks from merged M1 bars.
        Tick count per M1 bar equals M1 volume (at least 1).
        """
        m1 = self._prepare_m1_with_signals(trading_tf_data)
        manager = TimeframeManager()
        if not isinstance(m1.index, pd.DatetimeIndex):
            m1 = manager._ensure_datetime_index(m1)

        open_col = self._find_col(m1, ["Open"])
        high_col = self._find_col(m1, ["High"])
        low_col = self._find_col(m1, ["Low"])
        close_col = self._find_col(m1, ["Close"])
        volume_col = self._find_col(m1, ["Volume"])
        spread_col = self._find_col(m1, ["Spread"])
        if any(col is None for col in (open_col, high_col, low_col, close_col, volume_col)):
            raise ValueError(
                "synthetic_ticks requires M1 OHLCV columns: Open, High, Low, Close, Volume"
            )

        rows = []
        for ts, bar in m1.iterrows():
            open_px = float(bar[cast(str, open_col)])
            high_px = float(bar[cast(str, high_col)])
            low_px = float(bar[cast(str, low_col)])
            close_px = float(bar[cast(str, close_col)])
            vol = int(max(4, int(float(bar[cast(str, volume_col)]))))
            native_spread_points = (
                float(bar[spread_col]) if spread_col is not None and pd.notna(bar[spread_col]) else 0.0
            )

            if close_px >= open_px:
                path = [open_px, low_px, high_px, close_px]
            else:
                path = [open_px, high_px, low_px, close_px]
            prices = self._interpolate_path(path, vol)

            entry_signal = float(bar.get("entry_signal", 0.0) or 0.0)
            exit_signal = float(bar.get("exit_signal", 0.0) or 0.0)
            pending_signal = float(bar.get("pending_signal", 0.0) or 0.0)
            cancel_pending_signal = float(
                bar.get("cancel_pending_signal", 0.0) or 0.0
            )
            sl_value = float(bar.get("sl", 0.0) or 0.0)
            tp_value = float(bar.get("tp", 0.0) or 0.0)

            for i, px in enumerate(prices):
                spread_points = self._resolve_spread_points(native_spread_points)
                spread_price = spread_points * self.point_value
                # Spread ticks uniformly over the minute.
                offset_ms = int((60000.0 * i) / max(1, vol))
                tick_ts = ts + pd.to_timedelta(offset_ms, unit="ms")
                bid = float(px)
                ask = float(px + spread_price)
                rows.append(
                    {
                        "datetime": tick_ts,
                        "bid": bid,
                        "ask": ask,
                        "last": bid,
                        "spread": self._spread_points_to_int(spread_points),
                        "entry_signal": entry_signal if i == 0 else 0.0,
                        "exit_signal": exit_signal if i == 0 else 0.0,
                        "pending_signal": pending_signal if i == 0 else 0.0,
                        "cancel_pending_signal": (
                            cancel_pending_signal if i == 0 else 0.0
                        ),
                        "sl": sl_value if i == 0 else 0.0,
                        "tp": tp_value if i == 0 else 0.0,
                        "source_bar_time": ts,
                        "tick_index_in_bar": i,
                        "is_bar_close": (i == vol - 1),
                    }
                )

        ticks = pd.DataFrame(rows)
        if ticks.empty:
            return pd.DataFrame(
                columns=[
                    "bid",
                    "ask",
                    "last",
                    "spread",
                    "entry_signal",
                    "exit_signal",
                    "pending_signal",
                    "cancel_pending_signal",
                    "sl",
                    "tp",
                    "source_bar_time",
                    "tick_index_in_bar",
                ]
            )
        ticks = ticks.set_index("datetime")
        ticks.index = pd.DatetimeIndex(ticks.index, name="Datetime")
        return ticks.sort_index()



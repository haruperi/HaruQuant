"""Data Synchronization for Multi-Asset Portfolio Backtesting.

This module provides utilities to synchronize time-series data across multiple assets
with different trading hours, missing bars, and timestamps.
"""

import logging
from typing import Dict, Literal

import pandas as pd

logger = logging.getLogger(__name__)


class DataSynchronizer:
    """
    Synchronizes time-series data across multiple assets.

    Handles:
    - Different trading hours per symbol
    - Missing bars (forward-fill)
    - Different bar counts
    - Timezone alignment
    """

    @staticmethod
    def synchronize(  # noqa: C901
        data_dict: Dict[str, pd.DataFrame],
        method: Literal["ffill", "drop", "interpolate"] = "ffill",
        handle_leading_nans: Literal["drop", "fill"] = "drop",
        handle_trailing_nans: Literal["drop", "fill"] = "drop",
    ) -> Dict[str, pd.DataFrame]:
        """
        Synchronize multiple DataFrames to a common timeline.

        Args:
            data_dict: Dictionary mapping symbol to DataFrame (must have datetime index)
            method: How to handle missing bars:
                - 'ffill': Forward-fill missing values (default)
                - 'drop': Drop timestamps with any missing data
                - 'interpolate': Linear interpolation for missing values
            handle_leading_nans: How to handle NaNs at the start:
                - 'drop': Remove rows with NaNs at start (default)
                - 'fill': Forward-fill from first valid value
            handle_trailing_nans: How to handle NaNs at the end:
                - 'drop': Remove rows with NaNs at end (default)
                - 'fill': Forward-fill to end

        Returns:
            Dictionary mapping symbol to synchronized DataFrame

        Raises:
            ValueError: If data_dict is empty or DataFrames don't have datetime index
        """
        if not data_dict:
            raise ValueError("data_dict cannot be empty")

        # Validate inputs
        for symbol, df in data_dict.items():
            if df.empty:
                raise ValueError(f"DataFrame for {symbol} is empty")
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError(
                    f"DataFrame for {symbol} must have DatetimeIndex, got {type(df.index)}"
                )

        logger.info(f"Synchronizing {len(data_dict)} assets using method='{method}'")

        # Get union of all timestamps
        all_timestamps = pd.DatetimeIndex([])
        for df in data_dict.values():
            all_timestamps = all_timestamps.union(df.index)

        all_timestamps = all_timestamps.sort_values()
        logger.info(f"Common timeline: {len(all_timestamps)} total timestamps")

        # Reindex each DataFrame to common timeline (WITHOUT filling yet)
        synchronized = {}
        for symbol, df in data_dict.items():
            original_len = len(df)

            # Reindex to common timeline
            df_sync = df.reindex(all_timestamps)

            synchronized[symbol] = df_sync
            logger.debug(
                f"{symbol}: {original_len} → {len(df_sync)} bars after reindex"
            )

        # Determine common index based on leading/trailing NaN handling
        # We need to do this BEFORE applying fill methods
        final_index = all_timestamps

        # Handle leading/trailing NaN strategy
        # 'drop' = trim to common valid period
        # 'fill' = keep full timeline and fill NaNs
        if handle_leading_nans == "drop" or handle_trailing_nans == "drop":
            # Find valid ranges for each symbol
            if handle_leading_nans == "drop":
                # Find the latest first valid index across all symbols
                first_valid_indices = [
                    df.first_valid_index()
                    for df in synchronized.values()
                    if df.first_valid_index() is not None
                ]
                if first_valid_indices:
                    common_start = max(first_valid_indices)
                    final_index = final_index[final_index >= common_start]

            if handle_trailing_nans == "drop":
                # Find the earliest last valid index across all symbols
                last_valid_indices = [
                    df.last_valid_index()
                    for df in synchronized.values()
                    if df.last_valid_index() is not None
                ]
                if last_valid_indices:
                    common_end = min(last_valid_indices)
                    final_index = final_index[final_index <= common_end]

            # Apply final index to all DataFrames
            if len(final_index) < len(all_timestamps):
                synchronized = {
                    symbol: df.loc[final_index] for symbol, df in synchronized.items()
                }

        # Now apply fill methods to handle missing bars within the timeline
        if method == "ffill":
            synchronized = {symbol: df.ffill() for symbol, df in synchronized.items()}
            # If handle_*_nans='fill', also need to back-fill leading NaNs
            if handle_leading_nans == "fill":
                synchronized = {
                    symbol: df.bfill() for symbol, df in synchronized.items()
                }
        elif method == "interpolate":
            synchronized = {
                symbol: df.interpolate(method="linear")
                for symbol, df in synchronized.items()
            }
            if handle_leading_nans == "fill":
                synchronized = {
                    symbol: df.bfill() for symbol, df in synchronized.items()
                }
            if handle_trailing_nans == "fill":
                synchronized = {
                    symbol: df.ffill() for symbol, df in synchronized.items()
                }
        elif method == "drop":
            # Drop will be handled later (drop rows with any NaNs)
            pass
        else:
            raise ValueError(
                f"Invalid method: {method}. Must be 'ffill', 'drop', or 'interpolate'"
            )

        # If method='drop', remove timestamps with any NaNs across all symbols
        if method == "drop":
            # Find timestamps where ALL symbols have valid data
            common_index = final_index
            for _symbol, df in synchronized.items():
                # Keep only timestamps where this DataFrame has no NaNs
                valid_idx = df.dropna().index
                common_index = common_index.intersection(valid_idx)

            logger.info(f"After dropping NaNs: {len(common_index)} common timestamps")

            # Filter all DataFrames to common index
            synchronized = {
                symbol: df.loc[common_index] for symbol, df in synchronized.items()
            }

        # Final validation
        for symbol, df in synchronized.items():
            if df.empty:
                logger.warning(f"{symbol} has no data after synchronization")
            else:
                nan_count = df.isna().sum().sum()
                if nan_count > 0:
                    logger.warning(
                        f"{symbol} still has {nan_count} NaN values after synchronization"
                    )

        # Log final sizes
        final_sizes = {symbol: len(df) for symbol, df in synchronized.items()}
        logger.info(f"Synchronized data sizes: {final_sizes}")

        return synchronized

    @staticmethod
    def validate_synchronized_data(data_dict: Dict[str, pd.DataFrame]) -> bool:
        """
        Check if DataFrames are already synchronized (same index).

        Args:
            data_dict: Dictionary mapping symbol to DataFrame

        Returns:
            True if all DataFrames have identical index, False otherwise
        """
        if not data_dict:
            return False

        indices = [df.index for df in data_dict.values()]
        first_index = indices[0]

        return all(idx.equals(first_index) for idx in indices)

    @staticmethod
    def get_overlap_period(
        data_dict: Dict[str, pd.DataFrame]
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Get the overlapping time period across all DataFrames.

        Args:
            data_dict: Dictionary mapping symbol to DataFrame

        Returns:
            Tuple of (start_date, end_date) representing the overlap period

        Raises:
            ValueError: If there is no overlap
        """
        if not data_dict:
            raise ValueError("data_dict cannot be empty")

        # Get latest start date
        start_dates = [df.index.min() for df in data_dict.values()]
        overlap_start = max(start_dates)

        # Get earliest end date
        end_dates = [df.index.max() for df in data_dict.values()]
        overlap_end = min(end_dates)

        if overlap_start > overlap_end:
            raise ValueError(
                f"No overlap found: latest start={overlap_start}, earliest end={overlap_end}"
            )

        logger.info(f"Overlap period: {overlap_start} to {overlap_end}")
        return overlap_start, overlap_end

    @staticmethod
    def trim_to_overlap(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Trim all DataFrames to their overlapping time period.

        Args:
            data_dict: Dictionary mapping symbol to DataFrame

        Returns:
            Dictionary with DataFrames trimmed to overlap period
        """
        overlap_start, overlap_end = DataSynchronizer.get_overlap_period(data_dict)

        trimmed = {}
        for symbol, df in data_dict.items():
            df_trimmed = df.loc[overlap_start:overlap_end]
            trimmed[symbol] = df_trimmed
            logger.debug(
                f"{symbol}: {len(df)} → {len(df_trimmed)} bars (trimmed to overlap)"
            )

        return trimmed

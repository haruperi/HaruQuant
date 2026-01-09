"""
Dataframe Comparison Utility.

This module provides functionality to compare dataframes for equality,
specifically designed for comparing OHLCV data from different sources.
"""

from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from apps.logger import logger


def align_dataframes_by_datetime(
    df1: pd.DataFrame, df2: pd.DataFrame, verbose: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align two dataframes by finding the intersection of their datetime indices.

    This function:
    1. Finds the later start point between both dataframes
    2. Finds the earlier end point between both dataframes
    3. Returns sliced dataframes with only the intersecting datetime range

    Args:
        df1 (pd.DataFrame): First dataframe with datetime index
        df2 (pd.DataFrame): Second dataframe with datetime index
        verbose (bool): Whether to log alignment information (default: False)

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Aligned dataframes with intersecting datetime indices

    Raises:
        ValueError: If dataframes don't have datetime indices or no intersection found

    Example:
        >>> df1 = pd.DataFrame({'A': [1, 2, 3]}, index=pd.date_range('2025-01-01', periods=3))
        >>> df2 = pd.DataFrame({'A': [2, 3, 4, 5]}, index=pd.date_range('2025-01-02', periods=4))
        >>> aligned_df1, aligned_df2 = align_dataframes_by_datetime(df1, df2)
        >>> len(aligned_df1) == len(aligned_df2)
        True
    """
    # Validate that both dataframes have datetime indices
    if not isinstance(df1.index, pd.DatetimeIndex):
        raise ValueError("df1 must have a DatetimeIndex")
    if not isinstance(df2.index, pd.DatetimeIndex):
        raise ValueError("df2 must have a DatetimeIndex")

    # Normalize timezone information - convert both to timezone-naive for comparison
    df1_work = df1.copy()
    df2_work = df2.copy()

    df1_idx = df1_work.index
    df2_idx = df2_work.index

    if isinstance(df1_idx, pd.DatetimeIndex) and df1_idx.tz is not None:
        df1_work.index = df1_idx.tz_localize(None)
    if isinstance(df2_idx, pd.DatetimeIndex) and df2_idx.tz is not None:
        df2_work.index = df2_idx.tz_localize(None)

    if verbose:
        logger.info("Aligning dataframes by datetime index...")
        logger.info(
            f"  DF1 original range: {df1_work.index.min()} to {df1_work.index.max()} ({len(df1_work)} rows)"
        )
        logger.info(
            f"  DF2 original range: {df2_work.index.min()} to {df2_work.index.max()} ({len(df2_work)} rows)"
        )

    # Step 1: Find the later start point
    start_point = max(df1_work.index.min(), df2_work.index.min())

    # Step 2: Find the earlier end point
    end_point = min(df1_work.index.max(), df2_work.index.max())

    if verbose:
        logger.info(f"  Intersection range: {start_point} to {end_point}")

    # Validate that there's an intersection
    if start_point > end_point:
        raise ValueError(
            f"No datetime intersection found. "
            f"DF1 range: {df1_work.index.min()} to {df1_work.index.max()}, "
            f"DF2 range: {df2_work.index.min()} to {df2_work.index.max()}"
        )

    # Step 3: Slice both dataframes to the intersection range
    df1_aligned = df1_work.loc[start_point:end_point]
    df2_aligned = df2_work.loc[start_point:end_point]

    # Find common datetime indices (in case the dataframes don't have identical timestamps)
    common_index = df1_aligned.index.intersection(df2_aligned.index)

    if len(common_index) == 0:
        raise ValueError("No common datetime indices found in the intersection range")

    df1_aligned = df1_aligned.loc[common_index]
    df2_aligned = df2_aligned.loc[common_index]

    if verbose:
        logger.info(f"  Aligned DF1 shape: {df1_aligned.shape}")
        logger.info(f"  Aligned DF2 shape: {df2_aligned.shape}")
        logger.info(f"  Common datetime points: {len(common_index)}")

    return df1_aligned, df2_aligned


def compare_dataframes(  # noqa: C901
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    columns: Optional[Union[str, List[str]]] = None,
    tolerance: float = 1e-10,
    check_index: bool = False,
    align_by_datetime: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Compare two dataframes for equality in specified columns.

    Args:
        df1 (pd.DataFrame): First dataframe to compare
        df2 (pd.DataFrame): Second dataframe to compare
        columns (Union[str, List[str]], optional): Column(s) to compare.
            If None, compares all common columns. Can be a single column name
            or a list of column names.
        tolerance (float): Tolerance for floating point comparisons (default: 1e-10)
        check_index (bool): Whether to compare index values (default: False)
        align_by_datetime (bool): If True, align dataframes by datetime index intersection
            before comparison (default: False)
        verbose (bool): Whether to log detailed comparison information (default: False)

    Returns:
        bool: True if all specified columns are identical, False otherwise

    Raises:
        ValueError: If dataframes have different shapes (when align_by_datetime=False)
            or missing specified columns

    Example:
        >>> import pandas as pd
        >>> df1 = pd.DataFrame({'Open': [1.0, 2.0], 'High': [1.1, 2.1]})
        >>> df2 = pd.DataFrame({'Open': [1.0, 2.0], 'High': [1.1, 2.1]})
        >>> compare_dataframes(df1, df2, columns=['Open', 'High'])
        True

        >>> compare_dataframes(df1, df2, columns='Open')
        True
    """
    # Validate inputs
    if not isinstance(df1, pd.DataFrame) or not isinstance(df2, pd.DataFrame):
        raise TypeError("Both inputs must be pandas DataFrames")

    if verbose:
        logger.info("Comparing dataframes:")
        logger.info(f"  DF1 shape: {df1.shape}")
        logger.info(f"  DF2 shape: {df2.shape}")

    # Align by datetime if requested
    if align_by_datetime:
        df1, df2 = align_dataframes_by_datetime(df1, df2, verbose=verbose)

    # Handle columns parameter first
    if columns is None:
        # Compare all common columns
        columns_to_compare = list(set(df1.columns) & set(df2.columns))
        if len(columns_to_compare) == 0:
            if verbose:
                logger.error("❌ No common columns found")
            return False
        # For comparing all columns, shapes must match exactly
        if df1.shape != df2.shape:
            if verbose:
                logger.error("❌ Dataframes have different shapes")
            return False
    else:
        # Convert single column to list
        if isinstance(columns, str):
            columns_to_compare = [columns]
        else:
            columns_to_compare = columns

        # Check if specified columns exist in both dataframes
        missing_cols_df1 = [col for col in columns_to_compare if col not in df1.columns]
        missing_cols_df2 = [col for col in columns_to_compare if col not in df2.columns]

        if missing_cols_df1 or missing_cols_df2:
            error_msg = []
            if missing_cols_df1:
                error_msg.append(f"DF1 missing columns: {missing_cols_df1}")
            if missing_cols_df2:
                error_msg.append(f"DF2 missing columns: {missing_cols_df2}")
            raise ValueError(". ".join(error_msg))

        # For specific columns, only check that row count matches
        if len(df1) != len(df2):
            if verbose:
                logger.error(
                    f"❌ Dataframes have different number of rows: {len(df1)} vs {len(df2)}"
                )
            return False

    if verbose:
        logger.info(f"  Comparing columns: {columns_to_compare}")

    # Compare index if requested
    if check_index:
        if not df1.index.equals(df2.index):
            if verbose:
                logger.error("❌ Indices are not equal")
            return False
        elif verbose:
            logger.info("✅ Indices are equal")

    # Compare each specified column
    all_equal = True
    for col in columns_to_compare:
        col1_data = df1[col]
        col2_data = df2[col]

        # Handle different data types
        if col1_data.dtype != col2_data.dtype:
            if verbose:
                logger.error(
                    f"❌ Column '{col}' has different data types: {col1_data.dtype} vs {col2_data.dtype}"
                )
            all_equal = False
            continue

        # Compare based on data type
        if pd.api.types.is_numeric_dtype(col1_data):
            # For numeric data, use tolerance-based comparison
            if not _compare_numeric_series(col1_data, col2_data, tolerance):
                if verbose:
                    logger.error(
                        f"❌ Column '{col}' values are not equal (within tolerance {tolerance})"
                    )
                    _print_differences(col1_data, col2_data, col, tolerance)
                all_equal = False
            elif verbose:
                logger.info(f"✅ Column '{col}' values are equal")
        else:
            # For non-numeric data, use exact comparison
            if not col1_data.equals(col2_data):
                if verbose:
                    logger.error(f"❌ Column '{col}' values are not equal")
                    _print_differences(col1_data, col2_data, col)
                all_equal = False
            elif verbose:
                logger.info(f"✅ Column '{col}' values are equal")

    if verbose:
        result_symbol = "✅" if all_equal else "❌"
        logger.info(
            f"\n{result_symbol} Final result: {'EQUAL' if all_equal else 'NOT EQUAL'}"
        )

    return all_equal


def _compare_numeric_series(
    series1: pd.Series, series2: pd.Series, tolerance: float
) -> bool:
    """Compare two numeric series with tolerance for floating point precision issues."""
    try:
        # Handle NaN values
        if series1.isna().any() or series2.isna().any():
            # Check if NaN patterns match
            nan_mask1 = series1.isna()
            nan_mask2 = series2.isna()
            if not nan_mask1.equals(nan_mask2):
                return False

            # Compare non-NaN values
            non_nan_mask = ~(nan_mask1 | nan_mask2)
            if non_nan_mask.any():
                return bool(
                    np.allclose(
                        series1[non_nan_mask],
                        series2[non_nan_mask],
                        atol=tolerance,
                        rtol=tolerance,
                    )
                )
            else:
                return True  # All values are NaN
        else:
            # No NaN values, direct comparison
            return bool(np.allclose(series1, series2, atol=tolerance, rtol=tolerance))
    except Exception:
        # Fallback to exact comparison if allclose fails
        return bool(series1.equals(series2))


def _print_differences(
    series1: pd.Series,
    series2: pd.Series,
    column_name: str,
    tolerance: Optional[float] = None,
) -> None:
    """Log detailed information about differences between two series."""
    logger.info(f"    Differences in column '{column_name}':")

    if pd.api.types.is_numeric_dtype(series1) and tolerance is not None:
        # For numeric data
        diff = np.abs(series1 - series2)
        significant_diff = diff > tolerance

        if significant_diff.any():
            diff_indices = series1[significant_diff].index[
                :5
            ]  # Show first 5 differences
            logger.info(
                f"    First few significant differences (tolerance={tolerance}):"
            )
            for idx in diff_indices:
                series1_val = series1.loc[idx]
                series2_val = series2.loc[idx]
                diff_val = abs(series1_val - series2_val)
                logger.info(
                    f"      Index {idx}: {series1_val} vs {series2_val} (diff: {diff_val:.2e})"
                )
    else:
        # For non-numeric data
        different_mask = series1 != series2
        if different_mask.any():
            diff_indices = series1[different_mask].index[:5]  # Show first 5 differences
            logger.info("    First few differences:")
            for idx in diff_indices:
                logger.info(
                    f"      Index {idx}: '{series1.loc[idx]}' vs '{series2.loc[idx]}'"
                )


# Convenience functions for common OHLCV comparisons
def compare_ohlcv(df1: pd.DataFrame, df2: pd.DataFrame, **kwargs) -> bool:
    """
    Compare OHLCV (Open, High, Low, Close, Volume) columns between two dataframes.

    Args:
        df1, df2: DataFrames to compare
        **kwargs: Additional arguments passed to compare_dataframes()

    Returns:
        bool: True if all OHLCV columns are equal
    """
    ohlcv_columns = ["Open", "High", "Low", "Close", "Volume"]
    available_columns = [
        col for col in ohlcv_columns if col in df1.columns and col in df2.columns
    ]

    if not available_columns:
        raise ValueError("No OHLCV columns found in both dataframes")

    return compare_dataframes(df1, df2, columns=available_columns, **kwargs)


def compare_ohlc(df1: pd.DataFrame, df2: pd.DataFrame, **kwargs) -> bool:
    """
    Compare OHLC (Open, High, Low, Close) columns between two dataframes.

    Args:
        df1, df2: DataFrames to compare
        **kwargs: Additional arguments passed to compare_dataframes()

    Returns:
        bool: True if all OHLC columns are equal
    """
    ohlc_columns = ["Open", "High", "Low", "Close"]
    available_columns = [
        col for col in ohlc_columns if col in df1.columns and col in df2.columns
    ]

    if not available_columns:
        raise ValueError("No OHLC columns found in both dataframes")

    return compare_dataframes(df1, df2, columns=available_columns, **kwargs)

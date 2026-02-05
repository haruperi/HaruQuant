"""
Data Comparator Usage Examples

Purpose:
- Demonstrate DataFrame comparison for data validation
- Show OHLCV data comparison from different sources
- Illustrate datetime alignment for comparisons
- Examples for tolerance-based numeric comparisons

Key Concepts:
- compare_dataframes() for general comparison
- compare_ohlcv() and compare_ohlc() for market data
- align_dataframes_by_datetime() for different time ranges
- Tolerance settings for floating-point comparisons
- Detailed difference reporting

Usage:
    python tests/usage/utils/usage_data_comparator.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.data_comparator import (
    compare_dataframes,
    align_dataframes_by_datetime,
    compare_ohlcv,
    compare_ohlc,
)
from apps.utils.data_getters import load_dukascopy
from apps.logger import logger
import pandas as pd
import numpy as np


def example_01_identical_dataframes():
    """Example 1: Compare identical DataFrames."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Identical DataFrames Comparison")
    logger.info("=" * 70)

    # Create identical data
    dates = pd.date_range('2025-01-01', periods=10, freq='1h')
    df1 = pd.DataFrame({
        'open': [1.1000, 1.1010, 1.1020, 1.1030, 1.1040, 1.1050, 1.1060, 1.1070, 1.1080, 1.1090],
        'high': [1.1020, 1.1030, 1.1040, 1.1050, 1.1060, 1.1070, 1.1080, 1.1090, 1.1100, 1.1110],
        'low': [1.0990, 1.1000, 1.1010, 1.1020, 1.1030, 1.1040, 1.1050, 1.1060, 1.1070, 1.1080],
        'close': [1.1010, 1.1020, 1.1030, 1.1040, 1.1050, 1.1060, 1.1070, 1.1080, 1.1090, 1.1100],
    }, index=dates)

    df2 = df1.copy()

    logger.info("Comparing two identical DataFrames...")

    result = compare_dataframes(df1, df2, verbose=True)

    logger.info(f"\nComparison result: {'EQUAL' if result else 'NOT EQUAL'}")


def example_02_different_dataframes():
    """Example 2: Compare DataFrames with differences."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: DataFrames with Differences")
    logger.info("=" * 70)

    dates = pd.date_range('2025-01-01', periods=10, freq='1h')

    df1 = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 10),
        'close': np.random.uniform(1.10, 1.11, 10),
    }, index=dates)

    df2 = df1.copy()
    # Introduce differences
    df2.loc[dates[5], 'close'] += 0.01  # Significant difference

    logger.info("Comparing DataFrames with introduced differences...")

    result = compare_dataframes(df1, df2, verbose=True, tolerance=1e-5)

    logger.info(f"\nComparison result: {'EQUAL' if result else 'NOT EQUAL'}")


def example_03_tolerance_comparison():
    """Example 3: Tolerance-based comparison for floating point."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Tolerance-Based Comparison")
    logger.info("=" * 70)

    dates = pd.date_range('2025-01-01', periods=5, freq='1h')

    df1 = pd.DataFrame({
        'price': [1.10000, 1.10010, 1.10020, 1.10030, 1.10040]
    }, index=dates)

    df2 = pd.DataFrame({
        'price': [1.10000, 1.10010, 1.10021, 1.10030, 1.10040]  # Tiny difference
    }, index=dates)

    logger.info("Testing different tolerance levels...")

    # Strict tolerance
    result_strict = compare_dataframes(df1, df2, tolerance=1e-10, verbose=False)
    logger.info(f"Strict tolerance (1e-10): {'EQUAL' if result_strict else 'NOT EQUAL'}")

    # Relaxed tolerance
    result_relaxed = compare_dataframes(df1, df2, tolerance=1e-4, verbose=False)
    logger.info(f"Relaxed tolerance (1e-4): {'EQUAL' if result_relaxed else 'NOT EQUAL'}")


def example_04_specific_columns():
    """Example 4: Compare specific columns only."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Compare Specific Columns")
    logger.info("=" * 70)

    dates = pd.date_range('2025-01-01', periods=10, freq='1h')

    df1 = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 10),
        'high': np.random.uniform(1.11, 1.12, 10),
        'low': np.random.uniform(1.09, 1.10, 10),
        'close': np.random.uniform(1.10, 1.11, 10),
        'volume': np.random.randint(100, 200, 10),
    }, index=dates)

    df2 = df1.copy()
    # Change volume but keep OHLC same
    df2['volume'] = np.random.randint(150, 250, 10)

    logger.info("Comparing only OHLC columns (ignoring volume)...")

    result = compare_dataframes(
        df1, df2,
        columns=['open', 'high', 'low', 'close'],
        verbose=True
    )

    logger.info(f"\nOHLC comparison: {'EQUAL' if result else 'NOT EQUAL'}")


def example_05_single_column():
    """Example 5: Compare a single column."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Single Column Comparison")
    logger.info("=" * 70)

    dates = pd.date_range('2025-01-01', periods=10, freq='1h')

    df1 = pd.DataFrame({
        'close': [1.1000, 1.1010, 1.1020, 1.1030, 1.1040, 1.1050, 1.1060, 1.1070, 1.1080, 1.1090],
        'volume': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
    }, index=dates)

    df2 = df1.copy()

    logger.info("Comparing only 'close' column...")

    result = compare_dataframes(df1, df2, columns='close', verbose=True)

    logger.info(f"\nClose price comparison: {'EQUAL' if result else 'NOT EQUAL'}")


def example_06_datetime_alignment():
    """Example 6: Align DataFrames by datetime before comparison."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: DateTime Alignment")
    logger.info("=" * 70)

    # Create dataframes with different date ranges
    dates1 = pd.date_range('2025-01-01', periods=20, freq='1h')
    dates2 = pd.date_range('2025-01-01 05:00:00', periods=30, freq='1h')  # Starts later, ends later

    df1 = pd.DataFrame({
        'close': np.random.uniform(1.10, 1.11, 20)
    }, index=dates1)

    df2 = pd.DataFrame({
        'close': np.random.uniform(1.10, 1.11, 30)
    }, index=dates2)

    logger.info(f"DF1 range: {df1.index[0]} to {df1.index[-1]} ({len(df1)} rows)")
    logger.info(f"DF2 range: {df2.index[0]} to {df2.index[-1]} ({len(df2)} rows)")

    # Align before comparison
    df1_aligned, df2_aligned = align_dataframes_by_datetime(df1, df2, verbose=True)

    logger.info(f"\nAfter alignment:")
    logger.info(f"  DF1: {len(df1_aligned)} rows")
    logger.info(f"  DF2: {len(df2_aligned)} rows")
    logger.info(f"  Common range: {df1_aligned.index[0]} to {df1_aligned.index[-1]}")


def example_07_ohlcv_comparison():
    """Example 7: OHLCV-specific comparison."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: OHLCV Data Comparison")
    logger.info("=" * 70)

    dates = pd.date_range('2025-01-01', periods=10, freq='1h')

    df1 = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 10),
        'high': np.random.uniform(1.11, 1.12, 10),
        'low': np.random.uniform(1.09, 1.10, 10),
        'close': np.random.uniform(1.10, 1.11, 10),
        'volume': np.random.randint(100, 200, 10),
        'spread': np.random.uniform(0.0001, 0.0003, 10),
    }, index=dates)

    df2 = df1.copy()

    logger.info("Using compare_ohlcv() helper function...")

    result = compare_ohlcv(df1, df2, verbose=True)

    logger.info(f"\nOHLCV comparison: {'EQUAL' if result else 'NOT EQUAL'}")


def example_08_ohlc_only():
    """Example 8: OHLC-only comparison (without volume)."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: OHLC-Only Comparison")
    logger.info("=" * 70)

    dates = pd.date_range('2025-01-01', periods=10, freq='1h')

    df1 = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 10),
        'high': np.random.uniform(1.11, 1.12, 10),
        'low': np.random.uniform(1.09, 1.10, 10),
        'close': np.random.uniform(1.10, 1.11, 10),
        'volume': np.random.randint(100, 200, 10),
    }, index=dates)

    df2 = df1.copy()
    # Change volume
    df2['volume'] *= 2

    logger.info("Comparing OHLC only (ignoring volume)...")

    result = compare_ohlc(df1, df2, verbose=True)

    logger.info(f"\nOHLC comparison: {'EQUAL' if result else 'NOT EQUAL'}")


def example_09_real_data_sources():
    """Example 9: Compare data from different sources."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Compare Data from Different Sources")
    logger.info("=" * 70)

    logger.info("Loading same symbol data twice (should be identical)...")

    try:
        # Load same data twice
        df1 = load_dukascopy(symbol="EURUSD", timeframe="H1", count=100, cache=False)
        df2 = load_dukascopy(symbol="EURUSD", timeframe="H1", count=100, cache=False)

        logger.info(f"DF1: {len(df1)} bars")
        logger.info(f"DF2: {len(df2)} bars")

        # Compare
        result = compare_ohlcv(df1, df2, verbose=True, tolerance=1e-10)

        logger.info(f"\nData sources comparison: {'EQUAL' if result else 'NOT EQUAL'}")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")


def example_10_index_comparison():
    """Example 10: Compare including index values."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Index Comparison")
    logger.info("=" * 70)

    dates1 = pd.date_range('2025-01-01', periods=10, freq='1h')
    dates2 = pd.date_range('2025-01-01 00:00:01', periods=10, freq='1h')  # 1 second offset

    df1 = pd.DataFrame({
        'close': np.random.uniform(1.10, 1.11, 10)
    }, index=dates1)

    df2 = pd.DataFrame({
        'close': df1['close'].values  # Same values
    }, index=dates2)  # Different index

    logger.info("Comparing DataFrames with different index timestamps...")

    # Compare without checking index
    result_no_index = compare_dataframes(df1, df2, check_index=False, verbose=False)
    logger.info(f"Without index check: {'EQUAL' if result_no_index else 'NOT EQUAL'}")

    # Compare with index check
    result_with_index = compare_dataframes(df1, df2, check_index=True, verbose=True)
    logger.info(f"With index check: {'EQUAL' if result_with_index else 'NOT EQUAL'}")


def main():
    """Run all data comparator examples."""
    logger.info("\n" + "=" * 80)
    logger.info("DATA COMPARATOR - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_identical_dataframes()
    example_02_different_dataframes()
    example_03_tolerance_comparison()
    example_04_specific_columns()
    example_05_single_column()
    example_06_datetime_alignment()
    example_07_ohlcv_comparison()
    example_08_ohlc_only()
    example_09_real_data_sources()
    example_10_index_comparison()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. compare_dataframes() for general DataFrame comparison")
    logger.info("2. Use compare_ohlcv() and compare_ohlc() for market data")
    logger.info("3. Set tolerance for floating-point comparisons (default 1e-10)")
    logger.info("4. Use align_by_datetime=True for different date ranges")
    logger.info("5. Compare specific columns with columns parameter")
    logger.info("6. check_index=True to validate index equality")
    logger.info("7. verbose=True for detailed difference reporting")


if __name__ == "__main__":
    main()

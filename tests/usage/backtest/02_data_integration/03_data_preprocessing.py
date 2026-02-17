"""Example 03: Data Preprocessing

This example demonstrates how to clean and prepare data for backtesting.

Topics covered:
- Handling missing values
- Detecting and removing outliers
- Column standardization
- Index validation
- Data integrity checks
- Filling gaps in data

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402

from apps.utils.logger import logger  # noqa: E402
from apps.utils.data_validator import DataValidator  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def example1_handle_missing_values():
    """Detect and handle missing values."""
    print("\n" + "=" * 70)
    print("Example 1: Handling Missing Values")
    print("=" * 70)

    # Load data
    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-30"
    )

    print(f"\nOriginal data: {len(data):,} bars")

    # Check for missing values
    missing = data.isnull().sum()
    print("\nMissing values per column:")
    for col in data.columns:
        print(f"  {col}: {missing[col]}")

    total_missing = missing.sum()

    if total_missing == 0:
        print("\nNo missing values found - data is clean!")
    else:
        print(f"\nTotal missing values: {total_missing}")

        # Method 1: Forward fill
        print("\nMethod 1: Forward Fill (use previous value)")
        filled_ffill = data.fillna(method="ffill")
        print(f"  Remaining missing: {filled_ffill.isnull().sum().sum()}")

        # Method 2: Backward fill
        print("\nMethod 2: Backward Fill (use next value)")
        filled_bfill = data.fillna(method="bfill")
        print(f"  Remaining missing: {filled_bfill.isnull().sum().sum()}")

        # Method 3: Interpolation
        print("\nMethod 3: Linear Interpolation")
        filled_interp = data.interpolate(method="linear")
        print(f"  Remaining missing: {filled_interp.isnull().sum().sum()}")

        # Method 4: Drop rows with missing values
        print("\nMethod 4: Drop Missing Rows")
        dropped = data.dropna()
        print(f"  Rows dropped: {len(data) - len(dropped)}")
        print(f"  Remaining bars: {len(dropped):,}")

        print("\nRecommendation: Use forward fill for OHLCV data")


def example2_detect_outliers():
    """Detect outliers in price data."""
    print("\n" + "=" * 70)
    print("Example 2: Detecting Outliers")
    print("=" * 70)

    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-30"
    )

    print(f"\nAnalyzing {len(data):,} bars for outliers...")

    # Calculate returns
    returns = data["close"].pct_change()

    # Method 1: Z-score (statistical outliers)
    print("\nMethod 1: Z-Score (> 3 standard deviations)")
    mean_return = returns.mean()
    std_return = returns.std()
    z_scores = (returns - mean_return) / std_return
    outliers_z = abs(z_scores) > 3

    print(f"  Mean return: {mean_return * 100:.4f}%")
    print(f"  Std deviation: {std_return * 100:.4f}%")
    print(f"  Outliers found: {outliers_z.sum()}")

    if outliers_z.sum() > 0:
        print(f"  Max outlier: {returns[outliers_z].abs().max() * 100:.2f}%")

    # Method 2: IQR (Interquartile Range)
    print("\nMethod 2: IQR (Interquartile Range)")
    q1 = returns.quantile(0.25)
    q3 = returns.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers_iqr = (returns < lower_bound) | (returns > upper_bound)

    print(f"  Q1 (25%): {q1 * 100:.4f}%")
    print(f"  Q3 (75%): {q3 * 100:.4f}%")
    print(f"  IQR: {iqr * 100:.4f}%")
    print(f"  Outliers found: {outliers_iqr.sum()}")

    # Method 3: Absolute threshold
    print("\nMethod 3: Absolute Threshold (> 2% move)")
    threshold = 0.02  # 2%
    outliers_abs = abs(returns) > threshold
    print(f"  Threshold: {threshold * 100}%")
    print(f"  Outliers found: {outliers_abs.sum()}")

    if outliers_abs.sum() > 0:
        print("\n  Outlier examples:")
        outlier_data = data[outliers_abs].head(3)
        for idx, row in outlier_data.iterrows():
            ret = returns.loc[idx]
            print(f"    {idx}: {ret * 100:+.2f}% (close: {row['close']:.5f})")

    print("\nNote: Forex outliers are rare - most are legitimate price moves")


def example3_validate_ohlc():
    """Validate OHLC consistency."""
    print("\n" + "=" * 70)
    print("Example 3: OHLC Validation")
    print("=" * 70)

    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-30"
    )

    print(f"\nValidating {len(data):,} bars...")

    # Check 1: High >= Low
    invalid_hl = data["high"] < data["low"]
    print(f"\n1. High < Low: {invalid_hl.sum()} bars")

    # Check 2: High >= Open
    invalid_ho = data["high"] < data["open"]
    print(f"2. High < Open: {invalid_ho.sum()} bars")

    # Check 3: High >= Close
    invalid_hc = data["high"] < data["close"]
    print(f"3. High < Close: {invalid_hc.sum()} bars")

    # Check 4: Low <= Open
    invalid_lo = data["low"] > data["open"]
    print(f"4. Low > Open: {invalid_lo.sum()} bars")

    # Check 5: Low <= Close
    invalid_lc = data["low"] > data["close"]
    print(f"5. Low > Close: {invalid_lc.sum()} bars")

    # Check 6: Negative prices
    negative = (
        (data["open"] <= 0)
        | (data["high"] <= 0)
        | (data["low"] <= 0)
        | (data["close"] <= 0)
    )
    print(f"6. Negative/zero prices: {negative.sum()} bars")

    # Overall validation
    total_invalid = (
        invalid_hl.sum()
        + invalid_ho.sum()
        + invalid_hc.sum()
        + invalid_lo.sum()
        + invalid_lc.sum()
        + negative.sum()
    )

    print("\n" + "-" * 70)
    if total_invalid == 0:
        print("OHLC VALIDATION: PASSED - All bars are valid")
    else:
        print(f"OHLC VALIDATION: FAILED - {total_invalid} invalid bars found")
        print("Consider removing or correcting these bars")


def example4_detect_gaps():
    """Detect time gaps in data."""
    print("\n" + "=" * 70)
    print("Example 4: Detecting Time Gaps")
    print("=" * 70)

    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-30"
    )

    print(f"\nAnalyzing {len(data):,} bars for time gaps...")

    # Calculate time differences
    time_diff = data.index.to_series().diff()

    # Find the most common interval (mode)
    mode_interval = time_diff.mode()[0]
    print(f"\nExpected interval: {mode_interval}")

    # Find gaps (intervals larger than 1.5x the mode)
    threshold = mode_interval * 1.5
    gaps = time_diff > threshold

    print(f"Gaps detected: {gaps.sum()}")

    if gaps.sum() > 0:
        print("\nLargest gaps:")
        gap_data = time_diff[gaps].sort_values(ascending=False).head(5)

        for idx, gap_size in gap_data.items():
            prev_idx = data.index[data.index.get_loc(idx) - 1]
            print(f"  {prev_idx} -> {idx}: {gap_size}")

        print("\nNote: Gaps are normal during weekends and holidays")
    else:
        print("\nNo significant gaps detected")


def example5_standardize_columns():
    """Demonstrate column standardization."""
    print("\n" + "=" * 70)
    print("Example 5: Column Standardization")
    print("=" * 70)

    # Create sample data with non-standard columns
    print("\nCreating sample data with non-standard columns...")

    # Load real data first
    real_data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-30"
    )

    # Simulate non-standard format
    raw_data = real_data.copy()
    raw_data.columns = ["Open", "High", "Low", "Close", "Volume", "Spread"]  # Capitalized
    raw_data = raw_data.reset_index()  # Move index to column
    raw_data = raw_data.rename(columns={"index": "Timestamp"})  # Rename time column

    print("\nRaw data format:")
    print(f"  Columns: {list(raw_data.columns)}")
    print(f"  Index type: {type(raw_data.index).__name__}")
    print(raw_data.head(2))

    # Standardize using DataValidator.prepare_data()
    print("\nStandardizing with DataValidator.prepare_data()...")
    standardized = DataValidator.prepare_data(raw_data)

    print("\nStandardized data format:")
    print(f"  Columns: {list(standardized.columns)}")
    print(f"  Index type: {type(standardized.index).__name__}")
    print(standardized.head(2))

    print("\nChanges made:")
    print("  1. Columns converted to lowercase")
    print("  2. Timestamp column converted to DatetimeIndex")
    print("  3. Data sorted by index")
    print("  4. Only required columns retained")


def example6_complete_preprocessing():
    """Complete preprocessing workflow."""
    print("\n" + "=" * 70)
    print("Example 6: Complete Preprocessing Workflow")
    print("=" * 70)

    # Load raw data
    print("\n1. Loading raw data...")
    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-30"
    )
    print(f"   Loaded: {len(data):,} bars")

    # Step 1: Check for missing values
    print("\n2. Checking for missing values...")
    missing = data.isnull().sum().sum()
    print(f"   Missing values: {missing}")

    if missing > 0:
        print("   Filling missing values with forward fill...")
        data = data.fillna(method="ffill")
        data = data.fillna(method="bfill")  # Handle leading NaNs

    # Step 2: Validate OHLC
    print("\n3. Validating OHLC consistency...")
    invalid = (
        (data["high"] < data["low"])
        | (data["high"] < data["open"])
        | (data["high"] < data["close"])
        | (data["low"] > data["open"])
        | (data["low"] > data["close"])
    )
    print(f"   Invalid bars: {invalid.sum()}")

    if invalid.sum() > 0:
        print("   Removing invalid bars...")
        data = data[~invalid]

    # Step 3: Remove duplicates
    print("\n4. Checking for duplicate timestamps...")
    duplicates = data.index.duplicated().sum()
    print(f"   Duplicates: {duplicates}")

    if duplicates > 0:
        print("   Removing duplicates (keeping first)...")
        data = data[~data.index.duplicated(keep="first")]

    # Step 4: Sort by index
    print("\n5. Sorting by timestamp...")
    data = data.sort_index()

    # Step 5: Final validation
    print("\n6. Final validation...")
    print(f"   Total bars: {len(data):,}")
    print(f"   Date range: {data.index[0]} to {data.index[-1]}")
    print(f"   Missing values: {data.isnull().sum().sum()}")
    print(f"   Duplicates: {data.index.duplicated().sum()}")

    print("\n" + "-" * 70)
    print("PREPROCESSING COMPLETE - Data ready for backtesting")

    return data


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("DATA PREPROCESSING EXAMPLES")
    print("=" * 70)

    try:
        example1_handle_missing_values()
        example2_detect_outliers()
        example3_validate_ohlc()
        example4_detect_gaps()
        example5_standardize_columns()
        clean_data = example6_complete_preprocessing()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Always check for missing values and handle appropriately")
        print("2. Validate OHLC consistency before backtesting")
        print("3. Use DataValidator.prepare_data() to standardize formats")
        print("4. Time gaps are normal (weekends/holidays)")
        print("5. Outliers in forex are rare - most are legitimate moves")

        print("\nNext Steps:")
        print("- Try 04_multi_timeframe.py for multi-TF strategies")
        print("- Explore 05_custom_data_source.py for custom data")
        print("- Use cleaned data in your backtests")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()


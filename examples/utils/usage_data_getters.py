"""
Data Getters Usage Examples

Purpose:
- Demonstrate loading market data from multiple sources (MT5, Dukascopy, Parquet)
- Show data caching mechanisms for performance optimization
- Illustrate data preparation and validation workflows
- Examples for historical data retrieval and management

Key Concepts:
- MT5 data loading with fallback to Dukascopy
- Dukascopy API integration for historical data
- Parquet file loading for local data storage
- Data caching to avoid repeated API calls
- Automatic data preparation and validation

Usage:
    python tests/usage/utils/usage_data_getters.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.data_getters import (
    get_data_dir,
    load_parquet,
    load_dukascopy,
    load_mt5,
    clear_data_cache,
    get_cached_data,
)
from apps.utils.logger import logger


def example_01_get_data_directory():
    """Example 1: Get project data directory path."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Get Data Directory")
    logger.info("=" * 70)

    data_dir = get_data_dir()
    logger.info(f"Project data directory: {data_dir}")
    logger.info(f"Directory exists: {data_dir.exists()}")

    # Show subdirectories
    if data_dir.exists():
        subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
        logger.info(f"\nSubdirectories ({len(subdirs)}):")
        for subdir in subdirs[:5]:  # Show first 5
            logger.info(f"  - {subdir.name}")


def example_02_load_dukascopy_basic():
    """Example 2: Basic Dukascopy data loading."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Basic Dukascopy Data Loading")
    logger.info("=" * 70)

    # Load 30 days of EURUSD data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    logger.info(f"Loading EURUSD data from Dukascopy...")
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")

    try:
        df = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            cache=True
        )

        logger.info(f"\nData loaded successfully!")
        logger.info(f"Shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")

        logger.info("\nFirst 3 rows:")
        logger.info(df.head(3).to_string())

    except Exception as e:
        logger.error(f"Failed to load data: {e}")


def example_03_load_dukascopy_with_count():
    """Example 3: Load specific number of bars from Dukascopy."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Load Dukascopy Data by Bar Count")
    logger.info("=" * 70)

    # Load last 100 H1 bars
    logger.info("Loading last 100 H1 bars for GBPUSD...")

    try:
        df = load_dukascopy(
            symbol="GBPUSD",
            timeframe="H1",
            count=100,
            cache=True
        )

        logger.info(f"\nData loaded successfully!")
        logger.info(f"Number of bars: {len(df)}")
        logger.info(f"Latest bar: {df.index[-1]}")

        logger.info("\nLast 3 bars:")
        logger.info(df.tail(3).to_string())

        # Show OHLC statistics
        logger.info("\nOHLC Statistics:")
        logger.info(f"  High range: {df['high'].min():.5f} - {df['high'].max():.5f}")
        logger.info(f"  Low range: {df['low'].min():.5f} - {df['low'].max():.5f}")
        logger.info(f"  Average close: {df['close'].mean():.5f}")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")


def example_04_load_mt5_with_fallback():
    """Example 4: Load MT5 data with automatic Dukascopy fallback."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Load MT5 Data (with Dukascopy fallback)")
    logger.info("=" * 70)

    # Attempt to load from MT5, will fallback to Dukascopy if MT5 unavailable
    logger.info("Attempting to load EURUSD data...")
    logger.info("Will use MT5 if available, otherwise Dukascopy")

    try:
        df = load_mt5(
            symbol="EURUSD",
            timeframe="H1",
            count=200,
            user_id=1
        )

        if df is not None:
            logger.info(f"\nData loaded successfully!")
            logger.info(f"Shape: {df.shape}")
            logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")

            logger.info("\nData summary:")
            logger.info(df.describe().to_string())
        else:
            logger.warning("No data returned")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")


def example_05_load_mt5_date_range():
    """Example 5: Load MT5 data by date range."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Load MT5 Data by Date Range")
    logger.info("=" * 70)

    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 1, 31)

    logger.info(f"Loading USDJPY data from {start_date.date()} to {end_date.date()}")

    try:
        df = load_mt5(
            symbol="USDJPY",
            timeframe="H4",
            start_date=start_date,
            end_date=end_date,
            user_id=1
        )

        if df is not None:
            logger.info(f"\nData loaded!")
            logger.info(f"Bars: {len(df)}")
            logger.info(f"Timeframe: H4")

            logger.info("\nPrice movement:")
            logger.info(f"  Start: {df['close'].iloc[0]:.3f}")
            logger.info(f"  End: {df['close'].iloc[-1]:.3f}")
            logger.info(f"  Change: {df['close'].iloc[-1] - df['close'].iloc[0]:.3f}")
        else:
            logger.warning("No data returned")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")


def example_06_load_parquet_file():
    """Example 6: Load data from parquet file."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Load Data from Parquet File")
    logger.info("=" * 70)

    data_dir = get_data_dir()

    # Look for parquet files
    parquet_files = list(data_dir.rglob("*.parquet"))

    if parquet_files:
        # Load first parquet file found
        parquet_file = parquet_files[0]
        logger.info(f"Loading parquet file: {parquet_file.name}")

        try:
            df = load_parquet(parquet_file)

            logger.info(f"\nFile loaded successfully!")
            logger.info(f"Shape: {df.shape}")
            logger.info(f"Columns: {list(df.columns)}")

            if hasattr(df.index, 'min'):
                logger.info(f"Date range: {df.index.min()} to {df.index.max()}")

            logger.info("\nFirst few rows:")
            logger.info(df.head().to_string())

        except Exception as e:
            logger.error(f"Failed to load parquet: {e}")
    else:
        logger.warning(f"No parquet files found in {data_dir}")
        logger.info("\nTo create a parquet file, save DataFrame:")
        logger.info("  df.to_parquet('data/my_data.parquet')")


def example_07_caching_mechanism():
    """Example 7: Demonstrate data caching for performance."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Data Caching Mechanism")
    logger.info("=" * 70)

    import time

    # Clear cache first
    clear_data_cache()
    logger.info("Cache cleared")

    # First load (uncached)
    logger.info("\nFirst load (uncached)...")
    start_time = time.time()

    try:
        df1 = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            count=100,
            cache=True
        )
        first_load_time = time.time() - start_time
        logger.info(f"First load time: {first_load_time:.2f} seconds")

        # Second load (cached)
        logger.info("\nSecond load (cached)...")
        start_time = time.time()
        df2 = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            count=100,
            cache=True
        )
        second_load_time = time.time() - start_time
        logger.info(f"Second load time: {second_load_time:.2f} seconds")

        # Compare
        speedup = first_load_time / second_load_time if second_load_time > 0 else 0
        logger.info(f"\nCache speedup: {speedup:.1f}x faster")
        logger.info(f"Data identical: {df1.equals(df2)}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_08_multiple_symbols():
    """Example 8: Load data for multiple symbols."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Load Multiple Symbols")
    logger.info("=" * 70)

    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    data_dict = {}

    logger.info(f"Loading data for {len(symbols)} symbols...")

    for symbol in symbols:
        logger.info(f"\nLoading {symbol}...")
        try:
            df = load_dukascopy(
                symbol=symbol,
                timeframe="H1",
                count=50,
                cache=True
            )
            data_dict[symbol] = df
            logger.info(f"  Loaded {len(df)} bars")
            logger.info(f"  Latest close: {df['close'].iloc[-1]:.5f}")

        except Exception as e:
            logger.error(f"  Failed to load {symbol}: {e}")

    logger.info(f"\nSuccessfully loaded {len(data_dict)}/{len(symbols)} symbols")


def example_09_timezone_handling():
    """Example 9: Understanding timezone in loaded data."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Timezone Handling")
    logger.info("=" * 70)

    logger.info("Loading EURUSD data...")

    try:
        df = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            count=10,
            cache=False
        )

        logger.info(f"\nTimezone information:")
        logger.info(f"  Index type: {type(df.index)}")
        logger.info(f"  Has timezone: {df.index.tz is not None}")

        if df.index.tz is not None:
            logger.info(f"  Timezone: {df.index.tz}")
        else:
            logger.info(f"  Timezone: None (timezone-naive)")

        logger.info(f"\nFirst timestamp: {df.index[0]}")
        logger.info(f"Last timestamp: {df.index[-1]}")

        logger.info("\nNote: Dukascopy data is converted to Europe/Athens (EET/EEST)")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_10_data_validation():
    """Example 10: Data preparation and validation."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Data Preparation and Validation")
    logger.info("=" * 70)

    from apps.utils.data_validator import DataValidator

    logger.info("Loading and validating EURUSD data...")

    try:
        df = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            count=100,
            cache=True
        )

        logger.info(f"\nData loaded: {len(df)} bars")

        # The data is already prepared by load_dukascopy
        # Let's verify it has the expected structure
        logger.info("\nValidating data structure:")
        logger.info(f"  Has DatetimeIndex: {hasattr(df.index, 'tz')}")
        logger.info(f"  Has 'open' column: {'open' in df.columns}")
        logger.info(f"  Has 'high' column: {'high' in df.columns}")
        logger.info(f"  Has 'low' column: {'low' in df.columns}")
        logger.info(f"  Has 'close' column: {'close' in df.columns}")
        logger.info(f"  Has 'volume' column: {'volume' in df.columns}")
        logger.info(f"  Has 'spread' column: {'spread' in df.columns}")

        # Run validation
        validator = DataValidator()
        is_valid, df_marked, issues = validator.validate_price_sanity(df)

        logger.info(f"\nPrice sanity check:")
        logger.info(f"  Valid: {is_valid}")
        logger.info(f"  Issues found: {len(issues)}")

        if issues:
            logger.warning("Data quality issues detected:")
            for issue in issues[:3]:  # Show first 3
                logger.warning(f"  {issue}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def main():
    """Run all data getter examples."""
    logger.info("\n" + "=" * 80)
    logger.info("DATA GETTERS - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_get_data_directory()
    example_02_load_dukascopy_basic()
    example_03_load_dukascopy_with_count()
    example_04_load_mt5_with_fallback()
    example_05_load_mt5_date_range()
    example_06_load_parquet_file()
    example_07_caching_mechanism()
    example_08_multiple_symbols()
    example_09_timezone_handling()
    example_10_data_validation()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. Use load_mt5() for live MT5 connection (automatic Dukascopy fallback)")
    logger.info("2. Use load_dukascopy() for historical data from Dukascopy API")
    logger.info("3. Use load_parquet() for fast local file loading")
    logger.info("4. Enable caching (cache=True) to avoid repeated API calls")
    logger.info("5. All loaders return data with standard OHLCV columns and DatetimeIndex")
    logger.info("6. Data is automatically prepared and validated")


if __name__ == "__main__":
    main()


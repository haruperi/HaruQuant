"""Example 05: Custom Data Sources

This example demonstrates how to integrate custom data sources with the backtest system.

Topics covered:
- Loading data from CSV files
- Fetching data from REST APIs (simulated)
- Converting custom formats
- Using DataValidator.prepare_data() helper
- Exporting real data to custom formats
- Best practices for data integration

Note: All examples use REAL data from MT5 (or fallback source), not synthetic data.

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator  # noqa: E402
from apps.indicator import sma  # noqa: E402
from apps.utils.logger import logger  # noqa: E402
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_validator import DataValidator  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def example1_export_to_csv():
    """Export real data to CSV and reload it."""
    print("\n" + "=" * 70)
    print("Example 1: Export Real Data to CSV")
    print("=" * 70)

    # Load real data from MT5
    print("\nLoading real EURUSD data...")
    real_data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-15"
    )
    
    print(f"  Loaded {len(real_data):,} bars")
    print(f"  Date range: {real_data.index[0]} to {real_data.index[-1]}")

    # Export to CSV
    csv_path = project_root / "data" / "eurusd_sample.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    export_data = real_data.copy()
    export_data.index.name = "time"  # Use 'time' for compatibility
    export_data = export_data.reset_index()
    export_data.to_csv(csv_path, index=False)
    
    print(f"\nExported to: {csv_path}")

    # Reload from CSV
    print("\nReloading from CSV...")
    raw_data = pd.read_csv(csv_path)
    
    print(f"  Loaded {len(raw_data)} rows")
    print(f"  Columns: {list(raw_data.columns)}")

    # Prepare for backtesting
    print("\nPreparing for backtesting...")
    backtest_data = DataValidator.prepare_data(raw_data)

    print(f"  Prepared {len(backtest_data)} bars")
    print(f"  Columns: {list(backtest_data.columns)}")
    print(f"  Index type: {type(backtest_data.index).__name__}")

    print("\nCSV data is now ready for backtesting!")

    # Clean up
    csv_path.unlink()


def example2_api_format_conversion():
    """Convert API-style format to backtest format using real data."""
    print("\n" + "=" * 70)
    print("Example 2: API Format Conversion (Using Real Data)")
    print("=" * 70)

    print("\nLoading real data and converting to API format...")
    
    # Load real data
    real_data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-04"
    )
    
    # Take first 3 bars and convert to API-style format
    sample_bars = real_data.head(3)
    
    # Simulate API response format
    api_data = []
    for idx, row in sample_bars.iterrows():
        api_data.append({
            "time": idx.isoformat(),
            "o": row["open"],
            "h": row["high"],
            "l": row["low"],
            "c": row["close"],
            "v": row["volume"],
        })
    
    print(f"\nAPI-style data ({len(api_data)} bars):")
    for bar in api_data:
        print(f"  {bar}")

    # Convert to DataFrame
    print("\nConverting API response to DataFrame...")
    df = pd.DataFrame(api_data)

    # Rename columns to standard format
    df = df.rename(
        columns={
            "time": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        }
    )

    # Prepare for backtesting
    backtest_data = DataValidator.prepare_data(df)

    print("\nPrepared data:")
    print(backtest_data)

    print("\nAPI data conversion complete!")


def example3_custom_column_names():
    """Convert custom column names using real data."""
    print("\n" + "=" * 70)
    print("Example 3: Custom Column Names (Using Real Data)")
    print("=" * 70)

    print("\nLoading real data...")
    real_data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-05"
    )
    
    # Simulate custom column names
    custom_data = real_data.reset_index()
    custom_data = custom_data.rename(
        columns={
            "index": "Date",
            "open": "Price_Open",
            "high": "Price_High",
            "low": "Price_Low",
            "close": "Price_Close",
            "volume": "Trade_Volume",
            "spread": "Bid_Ask_Spread",
        }
    )

    print(f"\nCustom format ({len(custom_data)} bars):")
    print(f"  Columns: {list(custom_data.columns)}")
    print(custom_data.head(3))

    # Convert to standard format
    print("\nConverting to standard format...")

    standard_data = custom_data.rename(
        columns={
            "Date": "time",
            "Price_Open": "open",
            "Price_High": "high",
            "Price_Low": "low",
            "Price_Close": "close",
            "Trade_Volume": "volume",
            "Bid_Ask_Spread": "spread",
        }
    )

    # Prepare for backtesting
    backtest_data = DataValidator.prepare_data(standard_data)

    print("\nStandard format:")
    print(f"  Columns: {list(backtest_data.columns)}")
    print(backtest_data.head(3))

    print("\nConversion complete!")


def example4_backtest_real_data():
    """Run backtest with real data."""
    print("\n" + "=" * 70)
    print("Example 4: Backtesting with Real Data")
    print("=" * 70)

    # Load real data
    print("\nLoading real EURUSD data...")
    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-15"
    )
    
    print(f"  Loaded {len(data):,} bars")
    print(f"  Date range: {data.index[0]} to {data.index[-1]}")

    # Define simple strategy
    class SimpleMAStrategy(BaseStrategy):
        """Simple moving average crossover strategy."""

        def __init__(self, params=None):
            super().__init__(params)
            self.fast_window = self.params.get("fast_window", 10)
            self.slow_window = self.params.get("slow_window", 30)

        def on_init(self) -> None:
            logger.info("Simple MA strategy initialized")

        def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
            result = sma(data, window=self.fast_window)
            result = sma(result, window=self.slow_window)

            fast_col = f"sma_{self.fast_window}"
            slow_col = f"sma_{self.slow_window}"

            result["entry_signal"] = 0
            result["exit_signal"] = 0
            result["pending_signal"] = 0
            result["cancel_pending_signal"] = 0
            result["price"] = float("nan")

            buy = result[fast_col] > result[slow_col]
            sell = result[fast_col] < result[slow_col]

            result.loc[buy, "entry_signal"] = 1
            result.loc[buy, "price"] = result.loc[buy, "open"]
            result.loc[sell, "exit_signal"] = 1


            # Cleanup


            mt5_client.shutdown()


            


            return result

    # Run backtest
    print("\nRunning backtest on real data...")
    strategy = SimpleMAStrategy(params={"symbol": "EURUSD"})
    # Initialize strategy
    strategy.on_init()

    # Calculate signals
    data = strategy.on_bar(data)

    # Get MT5 client for symbol info
    mt5_client = get_mt5_client()

    # Setup simulator components
    account_info = AccountInfoSimulator(
        balance=10000.0,
        equity=10000.0,
        margin_free=10000.0,
    )
    symbol_info = SymbolInfoSimulator.from_mt5_symbol('EURUSD')
    symbol_info.symbol = 'EURUSD'

    # Create simulator
    simulator = TradeSimulator(
        simulator_name="Backtest_EURUSD",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={'EURUSD': symbol_info},
    )

    # Run simulation
    simulator.run(
        data=data,
        strategy=strategy,
        symbol='EURUSD',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="event_driven",
        commission_per_contract=0.0002,
        slippage_points=0,
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)

    print("\n" + "-" * 70)
    print("BACKTEST RESULTS")
    print("-" * 70)

    print(f"\nPerformance:")
    print(f"  Total Return: {result.total_return_pct:.2f}%")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")

    print(f"\nTrades:")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate:.2f}%")

    print("\nReal data backtest completed successfully!")


def example5_best_practices():
    """Best practices for custom data integration."""
    print("\n" + "=" * 70)
    print("Example 5: Best Practices")
    print("=" * 70)

    print("\n1. Always Use DataValidator.prepare_data():")
    print("   - Standardizes column names to lowercase")
    print("   - Converts to DatetimeIndex")
    print("   - Adds missing columns (e.g., spread)")
    print("   - Validates required columns")
    print("   - Sorts by timestamp")

    print("\n2. Required Columns:")
    print("   - open, high, low, close (OHLC prices)")
    print("   - volume (trading volume)")
    print("   - spread (bid-ask spread, or 0)")

    print("\n3. Index Requirements:")
    print("   - Must be DatetimeIndex")
    print("   - Must be sorted ascending")
    print("   - No duplicate timestamps")

    print("\n4. Data Quality Checks:")
    print("   - No missing values")
    print("   - Valid OHLC relationships (high >= low, etc.)")
    print("   - Positive prices and volumes")
    print("   - Reasonable spread values")

    print("\n5. Common Data Sources:")
    print("   a) CSV Files:")
    print("      df = pd.read_csv('data.csv')")
    print("      data = DataValidator.prepare_data(df)")
    print("\n   b) REST APIs:")
    print("      response = requests.get('api_url')")
    print("      df = pd.DataFrame(response.json())")
    print("      data = DataValidator.prepare_data(df)")
    print("\n   c) Databases:")
    print("      df = pd.read_sql('SELECT * FROM ohlcv', conn)")
    print("      data = DataValidator.prepare_data(df)")
    print("\n   d) MT5:")
    print("      data = load_mt5('EURUSD', timeframe='M1', start_date='2025-11-03')")
    print("      # Already in correct format!")

    print("\n6. Error Handling:")
    print("   try:")
    print("       data = DataValidator.prepare_data(raw_data)")
    print("   except ValueError as e:")
    print("       print(f'Data validation failed: {e}')")
    print("       # Fix data issues")

    print("\n7. Performance Tips:")
    print("   - Use parquet format for large datasets")
    print("   - Cache processed data")
    print("   - Filter date ranges before processing")
    print("   - Use appropriate data types (float32 vs float64)")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("CUSTOM DATA SOURCE EXAMPLES (USING REAL DATA)")
    print("=" * 70)

    try:
        example1_export_to_csv()
        example2_api_format_conversion()
        example3_custom_column_names()
        example4_backtest_real_data()
        example5_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Use DataValidator.prepare_data() to standardize any data source")
        print("2. Required columns: open, high, low, close, volume, spread")
        print("3. Index must be DatetimeIndex, sorted ascending")
        print("4. Validate data quality before backtesting")
        print("5. All examples use REAL data from MT5 (or fallback source)")

        print("\nNext Steps:")
        print("- Integrate your own data sources")
        print("- Explore advanced features (optimization, walk-forward)")
        print("- Build production-ready strategies")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()


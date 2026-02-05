"""Example 04: Multi-Timeframe Strategies

This example demonstrates how to use multiple timeframes in trading strategies.

Topics covered:
- Loading data for multiple timeframes
- Resampling M1 to higher timeframes
- Trend filtering with higher timeframe
- Signal generation on lower timeframe
- Aligning different timeframe data
- Complete multi-TF strategy example

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
from apps.indicator import rsi, sma  # noqa: E402
from apps.logger import logger  # noqa: E402
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_getters import load_dukascopy  # noqa: E402
from apps.utils.data_manipulator import TimeframeManager  # noqa: E402
from apps.utils.data_validator import DataValidator  # noqa: E402

TIMEFRAME_MANAGER = TimeframeManager()


def resample_data(
    data: pd.DataFrame, target_timeframe: str, source_timeframe: str = "M1"
) -> pd.DataFrame:
    """Resample and standardize data to keep OHLCV columns consistent."""
    resampled = TIMEFRAME_MANAGER.resample(
        data, target_timeframe=target_timeframe, source_timeframe=source_timeframe
    )
    return DataValidator.prepare_data(resampled)


def example1_load_multiple_timeframes():
    """Load data for multiple timeframes."""
    print("\n" + "=" * 70)
    print("Example 1: Loading Multiple Timeframes")
    print("=" * 70)

    # Load M1 data
    print("\nLoading M1 data...")
    m1_data = load_dukascopy("EURUSD", start_date="2025-11-03", end_date="2025-11-30")
    print(f"  M1 bars: {len(m1_data):,}")

    # Resample to H1
    print("\nResampling to H1...")
    h1_data = resample_data(m1_data, target_timeframe="H1", source_timeframe="M1")
    print(f"  H1 bars: {len(h1_data):,}")
    print(f"  Compression ratio: {len(m1_data) / len(h1_data):.1f}:1")

    # Resample to H4
    print("\nResampling to H4...")
    h4_data = resample_data(m1_data, target_timeframe="H4", source_timeframe="M1")
    print(f"  H4 bars: {len(h4_data):,}")
    print(f"  Compression ratio: {len(m1_data) / len(h4_data):.1f}:1")

    # Resample to D1
    print("\nResampling to D1...")
    d1_data = resample_data(m1_data, target_timeframe="D1", source_timeframe="M1")
    print(f"  D1 bars: {len(d1_data):,}")
    print(f"  Compression ratio: {len(m1_data) / len(d1_data):.1f}:1")

    print("\nTimeframe Summary:")
    print(f"  M1:  {len(m1_data):,} bars (base)")
    print(f"  H1:  {len(h1_data):,} bars ({len(m1_data) // len(h1_data)}x compression)")
    print(f"  H4:  {len(h4_data):,} bars ({len(m1_data) // len(h4_data)}x compression)")
    print(f"  D1:  {len(d1_data):,} bars ({len(m1_data) // len(d1_data)}x compression)")


def example2_align_timeframes():
    """Align data from different timeframes."""
    print("\n" + "=" * 70)
    print("Example 2: Aligning Different Timeframes")
    print("=" * 70)

    # Load and resample
    m1_data = load_dukascopy("EURUSD", start_date="2025-11-03", end_date="2025-11-30")
    h1_data = resample_data(m1_data, target_timeframe="H1")
    d1_data = resample_data(m1_data, target_timeframe="D1")

    print(f"\nOriginal data:")
    print(f"  M1: {len(m1_data):,} bars")
    print(f"  H1: {len(h1_data):,} bars")
    print(f"  D1: {len(d1_data):,} bars")

    # Method 1: Merge with forward fill (propagate higher TF values)
    print("\nMethod 1: Merge with forward fill")

    # Add D1 close to H1 data
    h1_with_d1 = h1_data.copy()
    h1_with_d1["d1_close"] = d1_data["close"].reindex(h1_data.index, method="ffill")

    print(f"  H1 bars with D1 data: {len(h1_with_d1):,}")
    print("\n  Sample (showing H1 close vs D1 close):")
    print(h1_with_d1[["close", "d1_close"]].head(10))

    # Method 2: Merge at specific times
    print("\nMethod 2: Merge at daily open (00:00)")
    daily_opens = h1_data[h1_data.index.hour == 0].copy()
    daily_opens["d1_close"] = d1_data["close"].reindex(daily_opens.index, method="ffill")

    print(f"  Daily open bars: {len(daily_opens)}")
    print("\n  Sample:")
    print(daily_opens[["close", "d1_close"]].head(5))


def example3_trend_filter():
    """Use higher timeframe for trend filtering."""
    print("\n" + "=" * 70)
    print("Example 3: Trend Filtering with Higher Timeframe")
    print("=" * 70)

    # Load data
    m1_data = load_dukascopy("EURUSD", start_date="2025-11-03", end_date="2025-11-30")
    h1_data = resample_data(m1_data, target_timeframe="H1")

    print(f"\nData loaded: {len(h1_data):,} H1 bars")

    # Calculate trend on H1 using moving averages
    h1_data["sma_20"] = h1_data["close"].rolling(20).mean()
    h1_data["sma_50"] = h1_data["close"].rolling(50).mean()

    # Define trend
    h1_data["trend"] = 0  # Neutral
    h1_data.loc[h1_data["sma_20"] > h1_data["sma_50"], "trend"] = 1  # Uptrend
    h1_data.loc[h1_data["sma_20"] < h1_data["sma_50"], "trend"] = -1  # Downtrend

    # Count trend periods
    uptrend_bars = (h1_data["trend"] == 1).sum()
    downtrend_bars = (h1_data["trend"] == -1).sum()
    neutral_bars = (h1_data["trend"] == 0).sum()

    print(f"\nTrend Analysis:")
    print(f"  Uptrend bars: {uptrend_bars} ({uptrend_bars / len(h1_data) * 100:.1f}%)")
    print(f"  Downtrend bars: {downtrend_bars} ({downtrend_bars / len(h1_data) * 100:.1f}%)")
    print(f"  Neutral bars: {neutral_bars} ({neutral_bars / len(h1_data) * 100:.1f}%)")

    print("\nExample: Filter signals by trend")
    print("  - Only take BUY signals when H1 trend is UP")
    print("  - Only take SELL signals when H1 trend is DOWN")
    print("  - This reduces false signals in choppy markets")


def example4_multi_tf_strategy():
    """Complete multi-timeframe strategy example."""
    print("\n" + "=" * 70)
    print("Example 4: Multi-Timeframe Strategy")
    print("=" * 70)

    print("\nStrategy: H1 trend filter + M15 entry signals")
    print("  - Use H1 for trend direction (SMA 20/50 crossover)")
    print("  - Use M15 for entry timing (RSI oversold/overbought)")
    print("  - Only trade in direction of H1 trend")

    # Load M1 data and resample
    m1_data = load_dukascopy("EURUSD", start_date="2025-11-03", end_date="2025-11-30")
    m15_data = resample_data(m1_data, target_timeframe="M15")
    h1_data = resample_data(m1_data, target_timeframe="H1")

    print(f"\nData loaded:")
    print(f"  M15: {len(m15_data):,} bars (for signals)")
    print(f"  H1:  {len(h1_data):,} bars (for trend)")

    # Define strategy
    class MultiTimeframeStrategy(BaseStrategy):
        """Multi-timeframe strategy with H1 trend filter and M15 RSI signals."""

        def __init__(self, params=None):
            super().__init__(params)
            self.rsi_period = self.params.get("rsi_period", 14)
            self.rsi_overbought = self.params.get("rsi_overbought", 70)
            self.rsi_oversold = self.params.get("rsi_oversold", 30)
            self.h1_fast = self.params.get("h1_fast", 20)
            self.h1_slow = self.params.get("h1_slow", 50)

        def on_init(self) -> None:
            logger.info("Multi-timeframe strategy initialized")

        def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
            result = rsi(data, period=self.rsi_period)

            h1_close = result[["close"]].resample("1h").last().dropna()
            h1_close = sma(h1_close, window=self.h1_fast)
            h1_close = sma(h1_close, window=self.h1_slow)

            fast_col = f"sma_{self.h1_fast}"
            slow_col = f"sma_{self.h1_slow}"
            trend = pd.Series(0, index=h1_close.index)
            trend.loc[h1_close[fast_col] > h1_close[slow_col]] = 1
            trend.loc[h1_close[fast_col] < h1_close[slow_col]] = -1

            result["trend"] = trend.reindex(result.index, method="ffill").fillna(0)

            rsi_col = f"rsi_{self.rsi_period}"
            result["entry_signal"] = 0
            result["exit_signal"] = 0
            result["pending_signal"] = 0
            result["cancel_pending_signal"] = 0
            result["price"] = float("nan")

            buy = (result["trend"] == 1) & (result[rsi_col] < self.rsi_oversold)
            sell = (result["trend"] == -1) & (result[rsi_col] > self.rsi_overbought)
            result.loc[buy, "entry_signal"] = 1
            result.loc[buy, "price"] = result.loc[buy, "open"]
            result.loc[sell, "entry_signal"] = -1
            result.loc[sell, "price"] = result.loc[sell, "open"]

            exit_long = result["trend"] == -1
            exit_short = result["trend"] == 1
            result.loc[exit_long, "exit_signal"] = 1
            result.loc[exit_short, "exit_signal"] = -1


            # Cleanup


            mt5_client.shutdown()


            


            return result

    # Run backtest
    print("\nRunning backtest...")
    strategy = MultiTimeframeStrategy(params={"symbol": "EURUSD"})
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

    # Display results
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
    print(f"  Profit Factor: {result.profit_factor:.2f}")

    print("\nStrategy Benefits:")
    print("  + Trend filter reduces false signals")
    print("  + RSI provides good entry timing")
    print("  + Multi-TF approach improves win rate")


def example5_best_practices():
    """Best practices for multi-timeframe strategies."""
    print("\n" + "=" * 70)
    print("Example 5: Multi-Timeframe Best Practices")
    print("=" * 70)

    print("\n1. Choose Appropriate Timeframe Ratios:")
    print("   - Use 3-5x ratio between timeframes")
    print("   - Example: M15 + H1 (4x) or H1 + H4 (4x)")
    print("   - Avoid: M1 + D1 (too large gap)")

    print("\n2. Higher Timeframe for Trend:")
    print("   - Use higher TF to identify overall direction")
    print("   - Common: Daily trend, H4 signals")
    print("   - Or: H4 trend, H1 signals")

    print("\n3. Lower Timeframe for Entries:")
    print("   - Use lower TF for precise entry timing")
    print("   - Wait for pullbacks in trend direction")
    print("   - Use oscillators (RSI, Stochastic)")

    print("\n4. Align Data Properly:")
    print("   - Use forward fill to propagate higher TF values")
    print("   - Ensure no look-ahead bias")
    print("   - Validate alignment before backtesting")

    print("\n5. Common Patterns:")
    print("   a) Trend + Pullback:")
    print("      - D1 trend (SMA 50/200)")
    print("      - H4 pullback (RSI oversold in uptrend)")
    print("   b) Breakout Confirmation:")
    print("      - H4 breakout level")
    print("      - H1 confirmation candle")
    print("   c) Multiple Confirmation:")
    print("      - D1 trend")
    print("      - H4 support/resistance")
    print("      - H1 entry signal")

    print("\n6. Performance Tips:")
    print("   - Resample once, cache result")
    print("   - Use vectorized operations")
    print("   - Avoid resampling in next() method")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MULTI-TIMEFRAME STRATEGY EXAMPLES")
    print("=" * 70)

    try:
        example1_load_multiple_timeframes()
        example2_align_timeframes()
        example3_trend_filter()
        example4_multi_tf_strategy()
        example5_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Use TimeframeManager.resample() to convert between timeframes")
        print("2. Higher timeframe for trend, lower for entries")
        print("3. Forward fill to align different timeframes")
        print("4. Multi-TF strategies reduce false signals")
        print("5. Choose appropriate timeframe ratios (3-5x)")

        print("\nNext Steps:")
        print("- Try 05_custom_data_source.py for custom data")
        print("- Experiment with different TF combinations")
        print("- Test your own multi-TF strategies")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

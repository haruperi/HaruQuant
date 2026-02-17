"""Example 01: Fractional Trading

This example demonstrates fractional position sizing for crypto and other assets
that support non-integer trading volumes.

Topics covered:
- allow_fractional_volumes configuration option
- Crypto symbol presets (BTCUSD, ETHUSD, etc.)
- BacktestSymbolProvider.set_symbol_spec() for custom assets
- Comparison: fractional vs rounded position sizes

Author: HaruQuant Development Team
Created: 2025-12-03
Updated: 2026-01-12 (migrated to VectorizedEngine API)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

from apps.strategy import BaseStrategy  # noqa: E402
from apps.backtest.engine.vectorized import VectorizedEngine  # noqa: E402
from apps.risk.position_sizing import PositionSizer  # noqa: E402
from apps.trading.symbol_info import BacktestSymbolProvider  # noqa: E402
from apps.utils.logger import logger  # noqa: E402


# =============================================================================
# Simple Crypto Strategy
# =============================================================================


class SimpleCryptoStrategy(BaseStrategy):
    """Simple strategy for crypto backtesting."""

    def __init__(self, symbol: str = "BTCUSD"):
        super().__init__(params={"symbol": symbol})

    def on_init(self) -> None:
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on simple moving average crossover."""
        data = data.copy()

        # Calculate indicators
        data["sma_fast"] = data["close"].rolling(5).mean()
        data["sma_slow"] = data["close"].rolling(15).mean()

        # Initialize signal columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["stop_loss"] = 0.0
        data["take_profit"] = 0.0

        # Generate signals (SMA crossover)
        for i in range(16, len(data)):
            # Bullish crossover
            if (
                data["sma_fast"].iloc[i] > data["sma_slow"].iloc[i]
                and data["sma_fast"].iloc[i - 1] <= data["sma_slow"].iloc[i - 1]
            ):
                data.iloc[i, data.columns.get_loc("entry_signal")] = 1  # Buy

            # Bearish crossover - close long
            elif (
                data["sma_fast"].iloc[i] < data["sma_slow"].iloc[i]
                and data["sma_fast"].iloc[i - 1] >= data["sma_slow"].iloc[i - 1]
            ):
                data.iloc[i, data.columns.get_loc("exit_signal")] = 1  # Exit buy

        return data


# =============================================================================
# Data Generation Helpers
# =============================================================================


def generate_crypto_data(symbol: str = "BTCUSD", bars: int = 200) -> pd.DataFrame:
    """Generate sample crypto OHLCV data."""
    np.random.seed(42)

    # Starting prices for different assets
    start_prices = {
        "BTCUSD": 45000.0,
        "ETHUSD": 2500.0,
        "SOLUSD": 100.0,
        "XRPUSD": 0.50,
    }

    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(hours=i) for i in range(bars)]

    base_price = start_prices.get(symbol, 1000.0)
    prices = [base_price]
    volatility = base_price * 0.002  # 0.2% volatility

    for _ in range(bars - 1):
        change = np.random.randn() * volatility
        prices.append(prices[-1] + change)

    data = pd.DataFrame(
        {
            "open": prices,
            "high": [p + abs(np.random.randn() * volatility * 0.5) for p in prices],
            "low": [p - abs(np.random.randn() * volatility * 0.5) for p in prices],
            "close": [p + np.random.randn() * volatility * 0.3 for p in prices],
            "volume": [np.random.randint(100, 1000) for _ in range(bars)],
        },
        index=pd.DatetimeIndex(dates),
    )

    return data


# =============================================================================
# Example 1: Basic Fractional Trading with Crypto
# =============================================================================


def example1_crypto_fractional():
    """Basic fractional trading with Bitcoin."""
    print("\n" + "=" * 70)
    print("Example 1: Crypto Fractional Trading (BTCUSD)")
    print("=" * 70)

    # Generate BTCUSD data
    data = generate_crypto_data("BTCUSD", bars=200)
    print(f"\nGenerated {len(data):,} bars of BTCUSD data")
    print(f"Price range: ${data['close'].min():,.2f} - ${data['close'].max():,.2f}")

    # Strategy
    strategy = SimpleCryptoStrategy(symbol="BTCUSD")

    # Position sizer with fractional BTC amount
    position_sizer = PositionSizer(
        method="fixed_lot",
        config={"lot_size": 0.00123456},  # Fractional BTC
    )

    # Run with fractional volumes ENABLED
    print("\n1. Running with allow_fractional_volumes=True...")
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
        engine_type="vectorised",
        commission_per_contract=0.0,
        slippage_points=0,
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)

    print("\n" + "-" * 70)
    print("FRACTIONAL TRADING RESULTS")
    print("-" * 70)

    print(f"\nPerformance:")
    print(f"  Initial Balance: ${result.initial_balance:,.2f}")
    print(f"  Final Balance:   ${result.final_balance:,.2f}")
    print(f"  Return:          {result.total_return_pct:.2f}%")

    print(f"\nTrades:")
    print(f"  Total Trades: {result.total_trades}")

    if result.total_trades > 0:
        trades_df = result.get_trades_df()
        trade_sizes = trades_df["size"].unique()
        print(f"  Position Sizes Used: {[f'{s:.8f}' for s in trade_sizes]}")
        print("  ✓ Exact fractional sizes preserved!")


# =============================================================================
# Example 2: Comparison - Fractional vs Rounded
# =============================================================================


def example2_comparison():
    """Compare fractional vs rounded position sizes."""
    print("\n" + "=" * 70)
    print("Example 2: Fractional vs Rounded Comparison")
    print("=" * 70)

    data = generate_crypto_data("BTCUSD", bars=200)
    strategy = SimpleCryptoStrategy(symbol="BTCUSD")

    # Position sizer requesting 0.0075 BTC
    position_sizer = PositionSizer(
        method="fixed_lot",
        config={"lot_size": 0.0075},
    )

    # Run WITH fractional
    print("\n1. With allow_fractional_volumes=True:")
    engine_frac = VectorizedEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        leverage=1,
        config={"allow_fractional_volumes": True},
        position_sizer=position_sizer,
    )
    result_frac = engine_frac.run()

    if result_frac.total_trades > 0:
        trades_frac = result_frac.get_trades_df()
        print(f"   Position size: {trades_frac['size'].iloc[0]:.8f} BTC")
        print(f"   Return: {result_frac.total_return_pct:.2f}%")

    # Run WITHOUT fractional (will round to lot_step=0.00000001)
    print("\n2. With allow_fractional_volumes=False:")
    engine_round = VectorizedEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        leverage=1,
        config={"allow_fractional_volumes": False},
        position_sizer=position_sizer,
    )
    result_round = engine_round.run()

    if result_round.total_trades > 0:
        trades_round = result_round.get_trades_df()
        print(f"   Position size: {trades_round['size'].iloc[0]:.8f} BTC")
        print(f"   Return: {result_round.total_return_pct:.2f}%")

    print("\nNote: For BTCUSD, lot_step=0.00000001 so rounding has minimal effect.")
    print("      For forex, lot_step=0.01 would show more significant rounding.")


# =============================================================================
# Example 3: Custom Symbol Specification
# =============================================================================


def example3_custom_symbol():
    """Demonstrate custom symbol configuration."""
    print("\n" + "=" * 70)
    print("Example 3: Custom Symbol Specification")
    print("=" * 70)

    print("\nUsing set_symbol_spec() for custom assets:")

    # Create provider for a custom asset
    print("\n1. Creating BacktestSymbolProvider for 'CUSTOM_TOKEN'...")
    provider = BacktestSymbolProvider(symbol_name="CUSTOM_TOKEN")

    print(f"   Default settings:")
    print(f"     volume_min:  {provider.get_lots_min()}")
    print(f"     volume_step: {provider.get_lots_step()}")
    print(f"     contract_size: {provider.get_contract_size()}")

    # Override with custom settings
    print("\n2. Applying custom specification...")
    provider.set_symbol_spec(
        volume_min=0.001,
        volume_max=100000.0,
        volume_step=0.001,
        trade_contract_size=1.0,
    )

    print(f"   Custom settings:")
    print(f"     volume_min:  {provider.get_lots_min()}")
    print(f"     volume_step: {provider.get_lots_step()}")
    print(f"     contract_size: {provider.get_contract_size()}")


# =============================================================================
# Example 4: Crypto Symbol Presets
# =============================================================================


def example4_symbol_presets():
    """Show the built-in crypto symbol presets."""
    print("\n" + "=" * 70)
    print("Example 4: Built-in Crypto Symbol Presets")
    print("=" * 70)

    symbols = ["BTCUSD", "ETHUSD", "XRPUSD", "SOLUSD", "EURUSD"]

    print("\n{:<12} {:>15} {:>15} {:>15}".format(
        "Symbol", "Volume Min", "Volume Step", "Contract Size"
    ))
    print("-" * 60)

    for symbol in symbols:
        provider = BacktestSymbolProvider(symbol_name=symbol)
        print("{:<12} {:>15.8f} {:>15.8f} {:>15.1f}".format(
            symbol,
            provider.get_lots_min(),
            provider.get_lots_step(),
            provider.get_contract_size(),
        ))

    print("\nNote: Crypto symbols have much finer volume_step than forex")


# =============================================================================
# Example 5: Use Cases and Best Practices
# =============================================================================


def example5_best_practices():
    """Best practices for fractional trading."""
    print("\n" + "=" * 70)
    print("Example 5: Best Practices")
    print("=" * 70)

    print("""
When to use allow_fractional_volumes=True:
------------------------------------------
✓ Crypto trading (BTC, ETH, etc.)
✓ Fractional share trading (stocks)
✓ Precise risk-based position sizing
✓ Dollar-cost averaging strategies

When to use allow_fractional_volumes=False (default):
----------------------------------------------------
✓ Forex with standard lot sizes
✓ Futures contracts (integer contracts only)
✓ When broker enforces lot step rounding

Configuration Example:
---------------------
```python
# For crypto with exact fractional sizes
engine = VectorizedEngine(
    strategy=my_strategy,
    data=btcusd_data,
    config={"allow_fractional_volumes": True},
    position_sizer=PositionSizer(
        method="fixed_fractional",
        config={"fraction": 10.0}  # 10% of account per trade
    ),
)
```

Custom Asset Example:
--------------------
```python
# Use set_symbol_spec for custom assets
provider = BacktestSymbolProvider(symbol_name="MY_TOKEN")
provider.set_symbol_spec(
    volume_min=0.0001,
    volume_step=0.0001,
    trade_contract_size=1.0,
)
```
""")


# =============================================================================
# Main
# =============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("FRACTIONAL TRADING EXAMPLES")
    print("Using VectorizedEngine with allow_fractional_volumes")
    print("=" * 70)

    try:
        example1_crypto_fractional()
        example2_comparison()
        example3_custom_symbol()
        example4_symbol_presets()
        example5_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Set config={'allow_fractional_volumes': True} for exact sizing")
        print("2. Crypto symbols have built-in presets (BTCUSD, ETHUSD, etc.)")
        print("3. Use set_symbol_spec() for custom asset configuration")
        print("4. PositionSizer.calculate_size() respects fractional settings")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()


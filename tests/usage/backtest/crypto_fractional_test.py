"""
Crypto Fractional Position Size Test.

Verifies that the backtest engine correctly handles fractional
position sizes for cryptocurrency assets like Bitcoin.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Simple test strategy for crypto
from apps.strategy import BaseStrategy


class SimpleCryptoStrategy(BaseStrategy):
    """Simple strategy that generates a buy signal on first bar."""

    def __init__(self, symbol: str = "BTCUSD"):
        super().__init__(params={"symbol": symbol})

    def on_init(self) -> None:
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals - buy on first bar, sell on last."""
        data = data.copy()
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["stop_loss"] = 0.0
        data["take_profit"] = 0.0

        if len(data) > 2:
            # Buy signal on first bar (after warmup)
            data.iloc[1, data.columns.get_loc("entry_signal")] = 1
            # Exit on second to last bar
            data.iloc[-2, data.columns.get_loc("exit_signal")] = 1

        return data


def generate_crypto_data(bars: int = 50) -> pd.DataFrame:
    """Generate sample BTCUSD OHLCV data."""
    np.random.seed(42)
    
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(hours=i) for i in range(bars)]
    
    # Start at 45000 with random walk
    base_price = 45000.0
    prices = [base_price]
    for _ in range(bars - 1):
        change = np.random.randn() * 100  # $100 volatility
        prices.append(prices[-1] + change)
    
    data = pd.DataFrame({
        "open": prices,
        "high": [p + abs(np.random.randn() * 50) for p in prices],
        "low": [p - abs(np.random.randn() * 50) for p in prices],
        "close": [p + np.random.randn() * 30 for p in prices],
        "volume": [np.random.randint(100, 1000) for _ in range(bars)],
    }, index=pd.DatetimeIndex(dates))
    
    return data


def test_vectorized_fractional():
    """Test VectorizedEngine with fractional crypto volumes."""
    from apps.backtest.engine.vectorized import VectorizedEngine
    from apps.risk.position_sizing import PositionSizer
    
    print("\n" + "=" * 60)
    print("Testing VectorizedEngine with Fractional Crypto Volumes")
    print("=" * 60)
    
    strategy = SimpleCryptoStrategy(symbol="BTCUSD")
    data = generate_crypto_data(50)
    
    # Use fixed lot sizer with fractional amount
    position_sizer = PositionSizer(
        method="fixed_lot",
        config={"lot_size": 0.00123456}  # Fractional BTC
    )
    
    # Test WITH fractional volumes enabled
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
    
    print(f"\nWith allow_fractional_volumes=True:")
    print(f"  Trades: {result.total_trades}")
    
    if result.total_trades > 0:
        trades_df = result.get_trades_df()
        print(f"  Position Size: {trades_df['size'].iloc[0]:.8f} BTC")
        
        # Should preserve exact fractional size
        expected_size = 0.00123456
        actual_size = trades_df['size'].iloc[0]
        
        if abs(actual_size - expected_size) < 1e-10:
            print(f"  ✓ Fractional size preserved correctly!")
        else:
            print(f"  ✗ Size mismatch: expected {expected_size}, got {actual_size}")
    
    # Test WITHOUT fractional volumes (should round)
    engine_rounded = VectorizedEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        commission=0.0,
        leverage=1,
        config={"allow_fractional_volumes": False},
        position_sizer=position_sizer,
    )
    
    result_rounded = engine_rounded.run()
    
    print(f"\nWith allow_fractional_volumes=False (default):")
    print(f"  Trades: {result_rounded.total_trades}")
    
    if result_rounded.total_trades > 0:
        trades_df = result_rounded.get_trades_df()
        print(f"  Position Size: {trades_df['size'].iloc[0]:.8f} BTC")
        print(f"  (Rounded to volume_step)")


def test_symbol_presets():
    """Test that crypto symbol presets are loaded correctly."""
    from apps.trading.symbol_info import BacktestSymbolProvider
    
    print("\n" + "=" * 60)
    print("Testing Crypto Symbol Presets")
    print("=" * 60)
    
    symbols = ["BTCUSD", "ETHUSD", "XRPUSD", "SOLUSD", "EURUSD"]
    
    for symbol in symbols:
        provider = BacktestSymbolProvider(symbol_name=symbol)
        volume_min = provider.get_lots_min()
        volume_step = provider.get_lots_step()
        contract_size = provider.get_contract_size()
        
        print(f"\n{symbol}:")
        print(f"  Volume Min:  {volume_min}")
        print(f"  Volume Step: {volume_step}")
        print(f"  Contract Size: {contract_size}")


def test_custom_symbol_spec():
    """Test custom symbol specification via set_symbol_spec."""
    from apps.trading.symbol_info import BacktestSymbolProvider
    
    print("\n" + "=" * 60)
    print("Testing Custom Symbol Specification")
    print("=" * 60)
    
    # Create provider with default forex settings
    provider = BacktestSymbolProvider(symbol_name="CUSTOM_ASSET")
    print(f"\nDefault volume_step: {provider.get_lots_step()}")
    
    # Override with custom crypto-like settings
    provider.set_symbol_spec(
        volume_min=0.0001,
        volume_max=10000.0,
        volume_step=0.0001,
        trade_contract_size=1.0,
    )
    
    print(f"After set_symbol_spec(): {provider.get_lots_step()}")
    print(f"Contract size: {provider.get_contract_size()}")


if __name__ == "__main__":
    test_symbol_presets()
    test_custom_symbol_spec()
    test_vectorized_fractional()
    
    print("\n" + "=" * 60)
    print("All verification tests completed!")
    print("=" * 60)

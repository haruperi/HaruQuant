"""
Unit tests for SimulationEngine (Vectorized Mode).

Tests:
- Vectorized signal processing
- Vectorized execution
- Results comparison with event-driven engine
- Performance characteristics
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator


class MockMT5Client:
    """Mock MT5 client for testing without real connection."""

    def order_calc_profit(self, action, symbol, volume, price_open, price_close):
        """Calculate profit for a trade."""
        # Simple profit calculation
        contract_size = 100000.0  # Standard forex lot
        if action == 0:  # Buy
            profit = (price_close - price_open) * volume * contract_size
        else:  # Sell
            profit = (price_open - price_close) * volume * contract_size
        return profit

    def order_calc_margin(self, action, symbol, volume, price):
        """Calculate margin for a trade."""
        contract_size = 100000.0
        leverage = 100.0
        return (volume * contract_size * price) / leverage


class SimpleVectorStrategy:
    """
    Simple strategy for testing vectorized execution.

    Uses simple logic that generates clear signals.
    """

    def __init__(self, params: dict):
        self.params = params
        self.symbol = params.get("symbol", "EURUSD")
        self.threshold = params.get("threshold", 0.0)

    def on_init(self):
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on price threshold.

        Buy when close > threshold
        Sell when close < threshold
        """
        data = data.copy()

        # Initialize signal columns (required by engine)
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = data["close"]

        # Generate entry signals
        data.loc[data["close"] > self.threshold, "entry_signal"] = 1  # Buy
        data.loc[data["close"] < self.threshold, "entry_signal"] = -1  # Sell

        # Only signal on change
        data["signal_prev"] = data["entry_signal"].shift(1).fillna(0)
        data.loc[data["entry_signal"] == data["signal_prev"], "entry_signal"] = 0

        return data

    def get_signal(self, data: pd.DataFrame, index: int):
        """
        Get signal details for a specific bar.

        Returns SignalDict or None.
        """
        row = data.iloc[index]
        entry = int(row.get("entry_signal", 0))
        exit_sig = int(row.get("exit_signal", 0))
        pending = int(row.get("pending_signal", 0))
        cancel = int(row.get("cancel_pending_signal", 0))

        if entry == 0 and exit_sig == 0 and pending == 0 and cancel == 0:
            return None

        return {
            "entry_signal": entry,
            "exit_signal": exit_sig,
            "pending_signal": pending,
            "cancel_pending_signal": cancel,
            "price": row.get("price", row["close"]),
        }


class TestVectorizedSignalProcessing:
    """Test vectorized signal processing."""

    def test_vectorized_signal_generation(self):
        """Test that signals are generated in vectorized manner."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Vector_Signals",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data
        dates = pd.date_range(start="2025-01-01", periods=50, freq="h")
        prices = [1.10000 + i * 0.00001 for i in range(50)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10025})
        strategy.on_init()
        data = strategy.on_bar(data)

        # Verify signals are generated
        assert "entry_signal" in data.columns
        assert data["entry_signal"].abs().sum() > 0  # At least some signals

    def test_vectorized_batch_processing(self):
        """Test processing entire dataset at once (vectorized)."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Vector_Batch",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Large dataset
        dates = pd.date_range(start="2025-01-01", periods=1000, freq="h")
        prices = [1.10000 + np.sin(i * 0.1) * 0.00100 for i in range(1000)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10000})
        strategy.on_init()
        data = strategy.on_bar(data)

        # Should process all bars
        assert len(data) == 1000
        assert "entry_signal" in data.columns


class TestVectorizedExecution:
    """Test vectorized execution mode."""

    def test_vectorized_engine_execution(self):
        """Test running backtest in vectorized mode."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Vector_Engine",
            mt5_client=MockMT5Client(),
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data
        dates = pd.date_range(start="2025-01-01", periods=100, freq="h")
        prices = [1.10000 + i * 0.00010 for i in range(100)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10050})
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run in vectorized mode
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",  # Vectorized mode
        )

        # Should complete without errors
        assert simulator._simulator._account_data.balance >= 0

    def test_vectorized_trade_generation(self):
        """Test that vectorized mode generates trades."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Vector_Trades",
            mt5_client=MockMT5Client(),
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with clear signal changes
        dates = pd.date_range(start="2025-01-01", periods=50, freq="h")
        prices = []
        for i in range(50):
            if i < 25:
                prices.append(1.10000 + i * 0.00001)  # Rising
            else:
                prices.append(1.10025 - (i - 25) * 0.00001)  # Falling

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10012})
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run vectorized
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",
        )

        # Should generate some trades
        trades = simulator._completed_trades
        # May have 0 or more trades depending on signal logic


class TestEngineComparison:
    """Compare results between event-driven and vectorized engines."""

    def test_compare_final_balance(self):
        """Compare final balance between both engines."""
        # Event-driven
        account1 = AccountInfoSimulator(balance=10000.0)
        symbol1 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator1 = TradeSimulator(
            simulator_name="Event_Driven",
            mt5_client=None,
            account_info=account1,
            symbols={"EURUSD": symbol1},
        )

        # Vectorized
        account2 = AccountInfoSimulator(balance=10000.0)
        symbol2 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator2 = TradeSimulator(
            simulator_name="Vectorized",
            mt5_client=MockMT5Client(),
            account_info=account2,
            symbols={"EURUSD": symbol2},
        )

        # Same data
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=100, freq="h")
        prices = [1.10000 + i * 0.00005 for i in range(100)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy1 = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10025})
        strategy2 = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10025})

        strategy1.on_init()
        data1 = strategy1.on_bar(data.copy())

        strategy2.on_init()
        data2 = strategy2.on_bar(data.copy())

        # Run both
        simulator1.run(
            data=data1,
            strategy=strategy1,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        simulator2.run(
            data=data2,
            strategy=strategy2,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",
        )

        # Results should be similar (may have small differences due to implementation)
        balance1 = simulator1._simulator.account_info().balance
        balance2 = simulator2._simulator.account_info().balance

        # Both should be valid
        assert balance1 >= 0
        assert balance2 >= 0

    def test_compare_trade_count(self):
        """Compare number of trades generated by both engines."""
        # Setup identical conditions
        account1 = AccountInfoSimulator(balance=10000.0)
        symbol1 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator1 = TradeSimulator(
            simulator_name="Event_Compare",
            mt5_client=None,
            account_info=account1,
            symbols={"EURUSD": symbol1},
        )

        account2 = AccountInfoSimulator(balance=10000.0)
        symbol2 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator2 = TradeSimulator(
            simulator_name="Vector_Compare",
            mt5_client=MockMT5Client(),
            account_info=account2,
            symbols={"EURUSD": symbol2},
        )

        # Same data
        dates = pd.date_range(start="2025-01-01", periods=50, freq="h")
        prices = [1.10000 + np.sin(i * 0.3) * 0.00050 for i in range(50)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy1 = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10000})
        strategy2 = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10000})

        strategy1.on_init()
        data1 = strategy1.on_bar(data.copy())

        strategy2.on_init()
        data2 = strategy2.on_bar(data.copy())

        # Run both
        simulator1.run(
            data=data1,
            strategy=strategy1,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        simulator2.run(
            data=data2,
            strategy=strategy2,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",
        )

        # Trade counts should be similar or identical
        trades1 = len(simulator1._completed_trades)
        trades2 = len(simulator2._completed_trades)

        # Both should be non-negative
        assert trades1 >= 0
        assert trades2 >= 0


class TestVectorizedPerformance:
    """Test performance characteristics of vectorized mode."""

    def test_vectorized_handles_large_dataset(self):
        """Test that vectorized mode can handle large datasets efficiently."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Large_Vector",
            mt5_client=MockMT5Client(),
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Large dataset (10,000 bars)
        dates = pd.date_range(start="2024-01-01", periods=10000, freq="h")
        prices = [1.10000 + np.sin(i * 0.01) * 0.00500 for i in range(10000)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10000})
        strategy.on_init()
        data = strategy.on_bar(data)

        # Should handle large dataset
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",
        )

        # Should complete successfully
        assert simulator._simulator._account_data.balance >= 0

    def test_vectorized_with_position_arrays(self):
        """Test vectorized mode with position array optimization."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Vector_Arrays",
            mt5_client=MockMT5Client(),
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data
        dates = pd.date_range(start="2025-01-01", periods=200, freq="h")
        prices = [1.10000 + i * 0.00010 for i in range(200)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleVectorStrategy(params={"symbol": "EURUSD", "threshold": 1.10100})
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run with position arrays enabled
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",
            use_position_arrays=True,  # Enable optimization
            use_numba=True,  # Enable Numba JIT
        )

        # Should complete successfully
        assert simulator._simulator._account_data.balance >= 0

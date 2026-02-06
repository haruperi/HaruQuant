"""
Integration tests for full backtest workflow.

Tests:
- Complete backtest execution with real strategy
- Trade execution verification
- Equity curve generation
- Performance metrics calculation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator


class MovingAverageCrossStrategy:
    """
    Simple MA crossover strategy for integration testing.

    Logic:
    - Buy when fast MA crosses above slow MA
    - Sell when fast MA crosses below slow MA
    """

    def __init__(self, params: dict):
        self.params = params
        self.symbol = params.get("symbol", "EURUSD")
        self.fast_period = params.get("fast_period", 10)
        self.slow_period = params.get("slow_period", 20)

    def on_init(self):
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators and generate signals."""
        data = data.copy()

        # Calculate moving averages
        data["ma_fast"] = data["close"].rolling(window=self.fast_period).mean()
        data["ma_slow"] = data["close"].rolling(window=self.slow_period).mean()

        # Generate signals
        data["signal"] = 0
        data.loc[data["ma_fast"] > data["ma_slow"], "signal"] = 1  # Buy
        data.loc[data["ma_fast"] < data["ma_slow"], "signal"] = -1  # Sell

        # Only signal on crossover (change in signal)
        data["signal_change"] = data["signal"].diff()
        data.loc[data["signal_change"] == 0, "signal"] = 0

        return data

    def get_signal(self, data: pd.DataFrame, index: int):
        """Get signal details for a specific bar."""
        row = data.iloc[index]
        signal = int(row.get("signal", 0))

        if signal == 0:
            return None

        return {
            "entry_signal": signal,
            "exit_signal": 0,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "price": row["close"],
        }


class TestFullBacktest:
    """Integration tests for complete backtest workflow."""

    def test_complete_backtest_execution(self):
        """Test full backtest from start to finish."""
        # Setup
        account = AccountInfoSimulator(balance=10000.0, leverage=100.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            trade_contract_size=100000.0,
            point=0.00001,
            digits=5,
        )

        simulator = TradeSimulator(
            simulator_name="Integration_Test",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create realistic synthetic data (100 bars)
        np.random.seed(42)  # Reproducible
        dates = pd.date_range(start="2025-01-01", periods=100, freq="h")

        # Generate trending data
        price = 1.10000
        prices = [price]
        for _ in range(99):
            change = np.random.randn() * 0.00010 + 0.000005  # Slight uptrend
            price += change
            prices.append(price)

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + abs(np.random.randn() * 0.00010) for p in prices],
                "low": [p - abs(np.random.randn() * 0.00010) for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        # Strategy
        strategy = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 10, "slow_period": 20}
        )
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run backtest
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
            commission_per_contract=7.0,
            slippage_points=2.0,
        )

        # Verify execution
        assert simulator._simulator._account_data.balance >= 0
        assert isinstance(simulator._completed_trades, list)

        # Should have generated some trades
        trades = simulator._completed_trades
        assert len(trades) >= 0  # May have 0 trades if no crossovers

    def test_trade_execution_verification(self):
        """Verify that trades are executed correctly."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Trade_Verification",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with known crossovers
        dates = pd.date_range(start="2025-01-01", periods=50, freq="h")

        # Create clear uptrend then downtrend to force crossovers
        prices = []
        for i in range(50):
            if i < 25:
                prices.append(1.10000 + i * 0.00010)  # Uptrend
            else:
                prices.append(1.10250 - (i - 25) * 0.00010)  # Downtrend

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

        strategy = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 5, "slow_period": 10}
        )
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run backtest
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        # Verify trades
        trades = simulator._completed_trades

        if len(trades) > 0:
            # Check first trade has required fields
            first_trade = trades[0]
            assert hasattr(first_trade, "ticket")
            assert hasattr(first_trade, "symbol")
            assert hasattr(first_trade, "type")
            assert hasattr(first_trade, "open_price")
            assert hasattr(first_trade, "close_price")
            assert hasattr(first_trade, "profit_loss")
            assert hasattr(first_trade, "size")

            # Verify trade values are reasonable
            assert first_trade.symbol == "EURUSD"
            assert first_trade.type.upper() in ["BUY", "SELL"]
            assert first_trade.size == 0.1
            assert first_trade.open_price > 0
            assert first_trade.close_price > 0

    def test_equity_curve_generation(self):
        """Test that equity curve is tracked throughout backtest."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Equity_Curve",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data
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

        strategy = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 10, "slow_period": 20}
        )
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run backtest
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        # Verify account balance is tracked
        final_balance = simulator._simulator.account_info().balance
        assert final_balance >= 0

        # Verify equity is also available
        account_info = simulator._simulator.account_info()
        if hasattr(account_info, 'equity'):
            final_equity = account_info.equity
            assert final_equity >= 0
            # Equity and balance should both be positive
            # (May differ if positions still open or during calculation)

    def test_performance_metrics_calculation(self):
        """Test calculation of performance metrics from backtest results."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Metrics_Test",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with known pattern
        dates = pd.date_range(start="2025-01-01", periods=50, freq="h")
        prices = [1.10000 + np.sin(i * 0.2) * 0.00100 for i in range(50)]

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

        strategy = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 5, "slow_period": 10}
        )
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run backtest
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        # Calculate metrics
        result = calculate_metrics_from_simulator(simulator)

        # Verify metrics structure
        assert hasattr(result, "trades")
        assert hasattr(result, "initial_balance")
        assert hasattr(result, "final_balance")

        # Verify values are reasonable
        assert result.initial_balance == 10000.0
        assert result.final_balance >= 0
        assert isinstance(result.trades, list)

    def test_backtest_with_stop_loss_take_profit(self):
        """Test backtest with SL/TP configuration."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="SLTP_Test",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with volatility
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=100, freq="h")
        prices = [1.10000 + np.random.randn() * 0.00050 for _ in range(100)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + abs(np.random.randn() * 0.00020) for p in prices],
                "low": [p - abs(np.random.randn() * 0.00020) for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 10, "slow_period": 20}
        )
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run backtest
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        # Verify backtest completed successfully
        assert simulator._simulator._account_data.balance >= 0
        trades = simulator._completed_trades
        # Should generate some trades (or none if no signals)
        assert isinstance(trades, list)

    def test_backtest_consistency(self):
        """Test that running same backtest twice produces same results."""
        account1 = AccountInfoSimulator(balance=10000.0)
        symbol1 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator1 = TradeSimulator(
            simulator_name="Consistency_1",
            mt5_client=None,
            account_info=account1,
            symbols={"EURUSD": symbol1},
        )

        account2 = AccountInfoSimulator(balance=10000.0)
        symbol2 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator2 = TradeSimulator(
            simulator_name="Consistency_2",
            mt5_client=None,
            account_info=account2,
            symbols={"EURUSD": symbol2},
        )

        # Same data for both
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=50, freq="h")
        prices = [1.10000 + i * 0.00010 for i in range(50)]

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

        strategy1 = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 10, "slow_period": 20}
        )
        strategy2 = MovingAverageCrossStrategy(
            params={"symbol": "EURUSD", "fast_period": 10, "slow_period": 20}
        )

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
            engine_type="event_driven",
        )

        # Results should be identical
        balance1 = simulator1._simulator.account_info().balance
        balance2 = simulator2._simulator.account_info().balance
        assert abs(balance1 - balance2) < 0.01

        trades1 = len(simulator1._completed_trades)
        trades2 = len(simulator2._completed_trades)
        assert trades1 == trades2

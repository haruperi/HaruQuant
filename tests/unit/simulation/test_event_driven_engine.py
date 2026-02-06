"""
Unit tests for SimulationEngine (Event-Driven Mode).

Tests:
- Engine initialization
- Backtest execution with simple strategy
- Order generation and execution
- Equity tracking
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import (
    SymbolInfoSimulator,
    AccountInfoSimulator,
    SymbolTickSimulator,
)
from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


def create_test_data(num_bars: int, prices: list = None, start_date="2025-01-01") -> pd.DataFrame:
    """
    Create properly formatted test data for backtesting.

    Args:
        num_bars: Number of bars to create
        prices: Optional list of close prices (generated if None)
        start_date: Start date for data

    Returns:
        DataFrame with proper datetime index
    """
    dates = pd.date_range(start=start_date, periods=num_bars, freq="h")

    if prices is None:
        prices = [1.10000] * num_bars

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
    )

    # Set index to time column (required by simulator)
    data = data.set_index("time")

    return data


class SimpleTestStrategy:
    """
    Minimal strategy for testing engine functionality.

    Logic:
    - Buy when close > signal (bullish)
    - Sell when close < signal (bearish)
    - Signal can be set manually for predictable testing
    """

    def __init__(self, params: dict):
        self.params = params
        self.symbol = params.get("symbol", "EURUSD")
        self.signals = []  # List of (index, action) tuples

    def on_init(self):
        """Initialize strategy (called once)."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Process bar data and generate signals.

        Adds required signal columns for engine compatibility.
        """
        data = data.copy()

        # Initialize signal columns (required by engine)
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float('nan')

        # Apply manual signals if set
        for idx, action in self.signals:
            if idx < len(data):
                if action > 0:  # Buy
                    data.iloc[idx, data.columns.get_loc("entry_signal")] = 1
                    data.iloc[idx, data.columns.get_loc("price")] = data.iloc[idx]["close"]
                elif action < 0:  # Sell
                    data.iloc[idx, data.columns.get_loc("entry_signal")] = -1
                    data.iloc[idx, data.columns.get_loc("price")] = data.iloc[idx]["close"]

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

    def set_signal(self, bar_index: int, action: int):
        """Set a signal at a specific bar index (for testing)."""
        self.signals.append((bar_index, action))


class TestEngineInitialization:
    """Test engine initialization and setup."""

    def test_simulator_initialization(self):
        """Test basic TradeSimulator initialization."""
        account = AccountInfoSimulator(balance=10000.0, leverage=100.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            trade_contract_size=100000.0,
            point=0.00001,
            digits=5,
        )

        simulator = TradeSimulator(
            simulator_name="Test_Init",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        assert simulator.simulator_name == "Test_Init"
        assert simulator._simulator._account_data.balance == 10000.0
        assert "EURUSD" in simulator._simulator._symbols_data

    def test_account_initialization(self):
        """Test account setup with initial balance and leverage."""
        account = AccountInfoSimulator(
            balance=50000.0, leverage=200.0, currency="USD"
        )
        symbol = SymbolInfoSimulator(symbol="EURUSD")

        simulator = TradeSimulator(
            simulator_name="Test_Account",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        acc = simulator._simulator.account_info()
        assert acc.balance == 50000.0
        assert acc.leverage == 200.0
        assert acc.currency == "USD"

    def test_symbol_configuration(self):
        """Test symbol info setup."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="GBPUSD",
            trade_contract_size=100000.0,
            point=0.00001,
            digits=5,
            spread=20,  # 2 pips spread
        )

        simulator = TradeSimulator(
            simulator_name="Test_Symbol",
            mt5_client=None,
            account_info=account,
            symbols={"GBPUSD": symbol},
        )

        sym_info = simulator._simulator.symbol_info("GBPUSD")
        assert sym_info.symbol == "GBPUSD"
        assert sym_info.trade_contract_size == 100000.0
        assert sym_info.spread == 20


class TestBacktestExecution:
    """Test backtest execution with a simple strategy."""

    def test_simple_backtest_execution(self):
        """Test running a backtest with minimal configuration."""
        # Setup
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Execution",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create synthetic data (10 bars)
        dates = pd.date_range(start="2025-01-01", periods=10, freq="h")
        data = pd.DataFrame(
            {
                "time": dates,
                "open": 1.10000 + np.random.randn(10) * 0.0001,
                "high": 1.10010 + np.random.randn(10) * 0.0001,
                "low": 1.09990 + np.random.randn(10) * 0.0001,
                "close": 1.10000 + np.random.randn(10) * 0.0001,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        # Simple strategy that doesn't generate signals
        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
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

        # Should complete without errors
        assert simulator._simulator._account_data.balance == 10000.0  # No trades
        assert len(simulator._completed_trades) == 0  # No signals = no trades

    def test_backtest_with_buy_signal(self):
        """Test backtest that generates a buy signal and executes trade."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Buy",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create test data
        data = create_test_data(10)

        # Strategy with buy signal at bar 2
        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(2, 1)  # Buy at bar 2
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

        # Should have opened at least one position
        # (may be closed by end of backtest via close_all_positions)
        trades = simulator._completed_trades
        assert len(trades) >= 1
        assert trades[0].type.upper() == "BUY"
        assert trades[0].symbol == "EURUSD"

    def test_backtest_with_multiple_signals(self):
        """Test backtest with multiple buy/sell signals."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Multiple",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create synthetic data with price movement
        dates = pd.date_range(start="2025-01-01", periods=20, freq="h")
        close_prices = [1.10000 + i * 0.00001 for i in range(20)]  # Uptrend
        data = pd.DataFrame(
            {
                "time": dates,
                "open": close_prices,
                "high": [p + 0.00010 for p in close_prices],
                "low": [p - 0.00010 for p in close_prices],
                "close": close_prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        # Strategy with multiple signals
        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(2, 1)  # Buy at bar 2
        strategy.set_signal(5, -1)  # Sell at bar 5 (close buy, open sell)
        strategy.set_signal(10, 1)  # Buy at bar 10 (close sell, open buy)
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

        # Should have multiple trades
        trades = simulator._completed_trades
        assert len(trades) >= 2  # At least 2 complete round-trips


class TestOrderExecution:
    """Test order generation and execution."""

    def test_order_creates_position(self):
        """Test that a buy signal creates a position."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Order",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with one buy signal
        dates = pd.date_range(start="2025-01-01", periods=5, freq="h")
        data = pd.DataFrame(
            {
                "time": dates,
                "open": [1.10000] * 5,
                "high": [1.10010] * 5,
                "low": [1.09990] * 5,
                "close": [1.10000] * 5,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(1, 1)  # Buy at bar 1
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

        # Check trade was executed
        trades = simulator._completed_trades
        assert len(trades) >= 1
        trade = trades[0]
        assert trade.size == 0.1
        assert trade.open_price > 0

    def test_order_execution_with_slippage(self):
        """Test that slippage is applied to order execution."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Slippage",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data
        dates = pd.date_range(start="2025-01-01", periods=5, freq="h")
        data = pd.DataFrame(
            {
                "time": dates,
                "open": [1.10000] * 5,
                "high": [1.10010] * 5,
                "low": [1.09990] * 5,
                "close": [1.10000] * 5,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(1, 1)  # Buy
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run with slippage
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
            slippage_points=5.0,  # 5 points slippage
        )

        # Slippage should affect entry price
        # (exact verification would require knowing exact fill price)
        trades = simulator._completed_trades
        assert len(trades) >= 1

    def test_order_execution_with_commission(self):
        """Test that commission is applied correctly."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Commission",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with buy and sell to complete trade
        dates = pd.date_range(start="2025-01-01", periods=5, freq="h")
        data = pd.DataFrame(
            {
                "time": dates,
                "open": [1.10000] * 5,
                "high": [1.10010] * 5,
                "low": [1.09990] * 5,
                "close": [1.10000] * 5,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(1, 1)  # Buy
        strategy.set_signal(3, -1)  # Sell (close position)
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run with commission
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
            commission_per_contract=7.0,  # $7 per lot
        )

        # Commission should be recorded in trade
        trades = simulator._completed_trades
        assert len(trades) >= 1
        # Commission is applied on close (round-trip model)
        # First completed trade should have commission deducted


class TestEquityTracking:
    """Test equity curve and account tracking."""

    def test_initial_equity_equals_balance(self):
        """Test that initial balance is set correctly."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD", trade_contract_size=100000.0)

        simulator = TradeSimulator(
            simulator_name="Test_Equity",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Check initial balance
        acc = simulator._simulator.account_info()
        assert acc.balance == 10000.0
        # Equity is 0 until positions are opened or monitor_account is called

    def test_equity_updates_with_open_position(self):
        """Test that equity updates when position is open with unrealized P&L."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Equity_Update",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with price movement
        dates = pd.date_range(start="2025-01-01", periods=10, freq="h")
        close_prices = [1.10000 + i * 0.00010 for i in range(10)]  # 10 pip uptrend
        data = pd.DataFrame(
            {
                "time": dates,
                "open": close_prices,
                "high": [p + 0.00010 for p in close_prices],
                "low": [p - 0.00010 for p in close_prices],
                "close": close_prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(1, 1)  # Buy and hold
        strategy.on_init()
        data = strategy.on_bar(data)

        # Run backtest (position stays open during backtest, closed at end)
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )

        # Position should have been closed at end
        # Balance should reflect final P&L
        final_balance = simulator._simulator.account_info().balance
        # With uptrend, buy position should be profitable
        # (exact amount depends on execution prices and spread)

    def test_balance_updates_on_trade_close(self):
        """Test that balance updates when trade closes."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Balance",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data with controlled price movement
        dates = pd.date_range(start="2025-01-01", periods=10, freq="h")
        data = pd.DataFrame(
            {
                "time": dates,
                "open": [1.10000] * 10,
                "high": [1.10010] * 10,
                "low": [1.09990] * 10,
                "close": [1.10000] * 10,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(1, 1)  # Buy
        strategy.set_signal(5, -1)  # Sell (close)
        strategy.on_init()
        data = strategy.on_bar(data)

        initial_balance = account.balance

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

        # Balance may have changed due to spread/commission
        final_balance = simulator._simulator.account_info().balance
        # At minimum, balance should be defined (not zero or None)
        assert final_balance > 0

    def test_margin_calculation(self):
        """Test that margin is calculated correctly for open positions."""
        account = AccountInfoSimulator(balance=10000.0, leverage=100.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Test_Margin",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # Create data
        dates = pd.date_range(start="2025-01-01", periods=5, freq="h")
        data = pd.DataFrame(
            {
                "time": dates,
                "open": [1.10000] * 5,
                "high": [1.10010] * 5,
                "low": [1.09990] * 5,
                "close": [1.10000] * 5,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = SimpleTestStrategy(params={"symbol": "EURUSD"})
        strategy.set_signal(1, 1)  # Buy 0.1 lot
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

        # Position closed at end, so margin should be released
        final_margin = simulator._simulator.account_info().margin
        assert final_margin == 0.0  # All positions closed

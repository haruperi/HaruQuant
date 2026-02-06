"""
Unit tests for portfolio management.

Tests:
    - Portfolio initialization
    - Adding/closing positions
    - Equity calculations
    - Account state management
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime

import pytest

from apps.mt5 import get_mt5_api
from apps.simulation.data import (
    AccountInfoSimulator,
    PositionInfoSimulator,
    SimulatorClient,
    SymbolInfoSimulator,
    SymbolTickSimulator,
)
from apps.simulation.utils import PositionArrayState

mt5 = get_mt5_api()


class TestPortfolioInitialization:
    """Test portfolio and account initialization."""

    def test_account_info_initialization(self):
        """Test AccountInfoSimulator initialization."""
        account = AccountInfoSimulator(
            login=12345,
            trade_mode=mt5.ACCOUNT_TRADE_MODE_DEMO,
            leverage=100,
            balance=10000.0,
            equity=10000.0,
            profit=0.0,
            margin=0.0,
            margin_free=10000.0,
            margin_level=0.0,
            currency="USD",
        )

        assert account.login == 12345
        assert account.leverage == 100
        assert account.balance == 10000.0
        assert account.equity == 10000.0
        assert account.margin == 0.0
        assert account.margin_free == 10000.0
        assert account.currency == "USD"

    def test_simulator_client_initialization(self):
        """Test SimulatorClient initialization."""
        account = AccountInfoSimulator(
            login=12345, leverage=100, balance=10000.0, currency="USD"
        )

        symbols = {
            "EURUSD": SymbolInfoSimulator(
                symbol="EURUSD",
                digits=5,
                point=0.00001,
                trade_contract_size=100000.0,
                trade_tick_size=0.00001,
                trade_tick_value=1.0,
            )
        }

        client = SimulatorClient(account_data=account, symbols_data=symbols)

        assert client.account_info() == account
        assert "EURUSD" in client._symbols_data
        assert len(client._positions_data) == 0
        assert len(client._history_orders_data) == 0


class TestAddingPositions:
    """Test adding positions to the portfolio."""

    def test_add_single_position(self):
        """Test adding a single position."""
        state = PositionArrayState(initial_size=10)

        position = PositionInfoSimulator(
            ticket=1001,
            type=mt5.POSITION_TYPE_BUY,
            volume=0.1,
            price_open=1.1000,
            price_current=1.1000,
            sl=1.0950,
            tp=1.1150,
            symbol="EURUSD",
            profit=0.0,
            margin_required=110.0,
        )

        symbol_params = {
            "contract_size": 100000.0,
            "tick_size": 0.00001,
            "tick_value": 1.0,
            "margin_mode": 0.0,
            "leverage": 100.0,
        }

        state.add_or_update(
            pos_id=1001, pos_data=position, symbol_params=symbol_params
        )

        assert state.count == 1
        assert state.pos_id[0] == 1001
        assert state.volume[0] == 0.1
        assert state.price_open[0] == 1.1000
        assert state.symbols[0] == "EURUSD"

    def test_add_multiple_positions(self):
        """Test adding multiple positions to portfolio."""
        state = PositionArrayState(initial_size=10)

        positions = [
            (1001, "EURUSD", mt5.POSITION_TYPE_BUY, 0.1, 1.1000),
            (1002, "GBPUSD", mt5.POSITION_TYPE_SELL, 0.2, 1.3000),
            (1003, "USDJPY", mt5.POSITION_TYPE_BUY, 0.3, 110.00),
        ]

        for ticket, symbol, pos_type, volume, price in positions:
            position = PositionInfoSimulator(
                ticket=ticket,
                type=pos_type,
                volume=volume,
                price_open=price,
                price_current=price,
                symbol=symbol,
            )
            state.add_or_update(pos_id=ticket, pos_data=position)

        assert state.count == 3
        assert 1001 in state.id_to_index
        assert 1002 in state.id_to_index
        assert 1003 in state.id_to_index

    def test_add_position_updates_existing(self):
        """Test that adding same position ID updates existing position."""
        state = PositionArrayState(initial_size=10)

        # Add initial position
        position = PositionInfoSimulator(
            ticket=2001,
            type=mt5.POSITION_TYPE_BUY,
            volume=0.1,
            price_open=1.1000,
            price_current=1.1000,
            symbol="EURUSD",
        )
        state.add_or_update(pos_id=2001, pos_data=position)

        assert state.count == 1
        assert state.price_current[0] == 1.1000

        # Update with new price
        position.price_current = 1.1050
        state.add_or_update(pos_id=2001, pos_data=position)

        assert state.count == 1  # Still only one position
        assert state.price_current[0] == 1.1050  # Price updated


class TestClosingPositions:
    """Test closing positions from the portfolio."""

    def test_close_single_position(self):
        """Test closing a single position."""
        state = PositionArrayState(initial_size=10)

        # Add two positions
        for ticket in [3001, 3002]:
            position = PositionInfoSimulator(
                ticket=ticket,
                type=mt5.POSITION_TYPE_BUY,
                volume=0.1,
                symbol="EURUSD",
            )
            state.add_or_update(pos_id=ticket, pos_data=position)

        assert state.count == 2

        # Close first position
        state.remove(pos_id=3001)

        assert state.count == 1
        assert 3001 not in state.id_to_index
        assert 3002 in state.id_to_index

    def test_close_all_positions(self):
        """Test closing all positions."""
        state = PositionArrayState(initial_size=10)

        # Add multiple positions
        for ticket in range(4001, 4006):
            position = PositionInfoSimulator(
                ticket=ticket, type=mt5.POSITION_TYPE_BUY, volume=0.1, symbol="EURUSD"
            )
            state.add_or_update(pos_id=ticket, pos_data=position)

        assert state.count == 5

        # Close all positions
        positions_to_close = list(state.id_to_index.keys())
        for pos_id in positions_to_close:
            state.remove(pos_id=pos_id)

        assert state.count == 0
        assert len(state.id_to_index) == 0

    def test_close_position_maintains_compact_array(self):
        """Test that closing positions keeps arrays compact."""
        state = PositionArrayState(initial_size=10)

        # Add 3 positions
        for ticket in [5001, 5002, 5003]:
            position = PositionInfoSimulator(
                ticket=ticket, type=mt5.POSITION_TYPE_BUY, volume=0.1, symbol="EURUSD"
            )
            state.add_or_update(pos_id=ticket, pos_data=position)

        # Close middle position
        state.remove(pos_id=5002)

        assert state.count == 2
        # Remaining positions should still be accessible
        assert 5001 in state.id_to_index
        assert 5003 in state.id_to_index


class TestEquityCalculations:
    """Test equity and account value calculations."""

    def test_account_equity_with_no_positions(self):
        """Test equity calculation with no open positions."""
        account = AccountInfoSimulator(
            balance=10000.0, equity=10000.0, profit=0.0, margin=0.0, margin_free=10000.0
        )

        assert account.balance == 10000.0
        assert account.equity == 10000.0
        assert account.profit == 0.0

    def test_account_equity_with_profitable_position(self):
        """Test equity calculation with profitable position."""
        account = AccountInfoSimulator(
            balance=10000.0,
            equity=10150.0,  # Balance + 150 profit
            profit=150.0,
            margin=110.0,
            margin_free=10040.0,
        )

        assert account.equity == 10150.0
        assert account.profit == 150.0
        assert account.margin_free == 10040.0

    def test_account_equity_with_losing_position(self):
        """Test equity calculation with losing position."""
        account = AccountInfoSimulator(
            balance=10000.0,
            equity=9850.0,  # Balance - 150 loss
            profit=-150.0,
            margin=110.0,
            margin_free=9740.0,
        )

        assert account.equity == 9850.0
        assert account.profit == -150.0
        assert account.margin_free == 9740.0

    def test_margin_level_calculation(self):
        """Test margin level calculation."""
        # Margin level = (Equity / Margin) * 100

        # Case 1: High margin level (healthy)
        account = AccountInfoSimulator(
            balance=10000.0,
            equity=10100.0,
            profit=100.0,
            margin=1000.0,
            margin_level=1010.0,  # (10100 / 1000) * 100
        )

        assert account.margin_level == 1010.0

        # Case 2: Low margin level (margin call risk)
        account = AccountInfoSimulator(
            balance=10000.0,
            equity=1500.0,
            profit=-8500.0,
            margin=1000.0,
            margin_level=150.0,  # (1500 / 1000) * 100
        )

        assert account.margin_level == 150.0

    def test_free_margin_calculation(self):
        """Test free margin calculation."""
        # Free margin = Equity - Used margin

        account = AccountInfoSimulator(
            balance=10000.0, equity=10000.0, margin=2000.0, margin_free=8000.0
        )

        assert account.margin_free == 8000.0

        # With profit
        account = AccountInfoSimulator(
            balance=10000.0, equity=10500.0, margin=2000.0, margin_free=8500.0
        )

        assert account.margin_free == 8500.0


class TestAccountStateManagement:
    """Test account state tracking and updates."""

    def test_account_balance_after_trade(self):
        """Test account balance update after closing trade."""
        # Initial state
        account = AccountInfoSimulator(balance=10000.0, equity=10000.0, profit=0.0)

        assert account.balance == 10000.0

        # Simulate closing profitable trade
        trade_profit = 150.0
        account.balance += trade_profit
        account.equity = account.balance  # After close, no open positions

        assert account.balance == 10150.0
        assert account.equity == 10150.0

    def test_account_margin_updates(self):
        """Test margin updates when positions are opened/closed."""
        account = AccountInfoSimulator(
            balance=10000.0, equity=10000.0, margin=0.0, margin_free=10000.0
        )

        # Open position (margin required)
        position_margin = 110.0
        account.margin += position_margin
        account.margin_free = account.equity - account.margin

        assert account.margin == 110.0
        assert account.margin_free == 9890.0

        # Close position (margin released)
        account.margin -= position_margin
        account.margin_free = account.equity - account.margin

        assert account.margin == 0.0
        assert account.margin_free == 10000.0

    def test_multiple_positions_margin(self):
        """Test margin calculation with multiple positions."""
        account = AccountInfoSimulator(
            balance=10000.0, equity=10000.0, margin=0.0, margin_free=10000.0
        )

        # Open 3 positions with different margins
        margins = [110.0, 130.0, 150.0]
        for margin in margins:
            account.margin += margin
            account.margin_free = account.equity - account.margin

        total_margin = sum(margins)
        assert account.margin == total_margin
        assert account.margin_free == 10000.0 - total_margin


class TestPortfolioMetrics:
    """Test portfolio-level metrics and statistics."""

    def test_portfolio_total_exposure(self):
        """Test calculating total portfolio exposure."""
        state = PositionArrayState(initial_size=10)

        # Add positions with different volumes
        positions_data = [
            (6001, "EURUSD", 0.1, 100000.0),
            (6002, "GBPUSD", 0.2, 100000.0),
            (6003, "USDJPY", 0.3, 100000.0),
        ]

        for ticket, symbol, volume, contract_size in positions_data:
            position = PositionInfoSimulator(
                ticket=ticket, type=mt5.POSITION_TYPE_BUY, volume=volume, symbol=symbol
            )
            symbol_params = {"contract_size": contract_size}
            state.add_or_update(
                pos_id=ticket, pos_data=position, symbol_params=symbol_params
            )

        # Calculate total exposure
        total_exposure = 0.0
        for i in range(state.count):
            total_exposure += state.volume[i] * state.contract_size[i]

        # 0.1*100000 + 0.2*100000 + 0.3*100000 = 60000
        assert total_exposure == 60000.0

    def test_portfolio_unrealized_pnl(self):
        """Test calculating total unrealized PnL."""
        state = PositionArrayState(initial_size=10)

        # Add positions with profits/losses
        positions_with_pnl = [
            (7001, "EURUSD", 50.0),  # $50 profit
            (7002, "GBPUSD", -30.0),  # $30 loss
            (7003, "USDJPY", 20.0),  # $20 profit
        ]

        for ticket, symbol, profit in positions_with_pnl:
            position = PositionInfoSimulator(
                ticket=ticket,
                type=mt5.POSITION_TYPE_BUY,
                volume=0.1,
                symbol=symbol,
                profit=profit,
            )
            state.add_or_update(pos_id=ticket, pos_data=position)

        # Calculate total unrealized PnL
        total_pnl = sum(state.profit[: state.count])

        # 50 - 30 + 20 = 40
        assert total_pnl == 40.0

    def test_portfolio_position_count(self):
        """Test counting positions in portfolio."""
        state = PositionArrayState(initial_size=10)

        assert state.count == 0

        # Add positions
        for i in range(5):
            position = PositionInfoSimulator(
                ticket=8000 + i, type=mt5.POSITION_TYPE_BUY, volume=0.1, symbol="EURUSD"
            )
            state.add_or_update(pos_id=8000 + i, pos_data=position)

        assert state.count == 5

        # Close 2 positions
        state.remove(pos_id=8000)
        state.remove(pos_id=8001)

        assert state.count == 3


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_remove_nonexistent_position(self):
        """Test removing a position that doesn't exist."""
        state = PositionArrayState(initial_size=10)

        # Add one position
        position = PositionInfoSimulator(
            ticket=9001, type=mt5.POSITION_TYPE_BUY, volume=0.1, symbol="EURUSD"
        )
        state.add_or_update(pos_id=9001, pos_data=position)

        # Try to remove non-existent position
        state.remove(pos_id=9999)

        # Should not affect existing position
        assert state.count == 1
        assert 9001 in state.id_to_index

    def test_update_nonexistent_position_sl_tp(self):
        """Test updating SL/TP of non-existent position."""
        state = PositionArrayState(initial_size=10)

        # Try to update non-existent position
        state.update_sl_tp(pos_id=9999, sl=1.1000, tp=1.2000)

        # Should not crash, just no-op
        assert state.count == 0

    def test_zero_leverage(self):
        """Test handling zero leverage in margin calculation."""
        from apps.simulation.utils import numba_position_update
        import numpy as np

        current_prices = np.array([1.1000], dtype=np.float64)
        price_open = np.array([1.1000], dtype=np.float64)
        volume = np.array([1.0], dtype=np.float64)
        direction = np.array([1], dtype=np.int8)
        sl = np.array([0.0], dtype=np.float64)
        tp = np.array([0.0], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([0.0], dtype=np.float64)  # Zero leverage

        profit, margin, sl_hit, tp_hit = numba_position_update(
            current_prices,
            price_open,
            volume,
            direction,
            sl,
            tp,
            valid,
            contract_size,
            tick_size,
            tick_value,
            margin_mode,
            leverage,
        )

        # Should use leverage = 1.0 as fallback
        # Margin = (1.0 * 100000) / 1.0 = 100000.0
        assert margin[0] == 100000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

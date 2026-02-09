"""
Unit tests for position tracking and management.

Tests:
    - Position creation and tracking
    - PnL calculations
    - Position updates (price, SL/TP, volume)
    - Position state management
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from apps.mt5 import get_mt5_api
from apps.simulation.data import PositionInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import PositionArrayState, numba_position_update

mt5 = get_mt5_api()


class TestPositionCreation:
    """Test position creation and initialization."""

    def test_position_info_simulator_creation(self):
        """Test creating a PositionInfoSimulator object."""
        position = PositionInfoSimulator(
            ticket=12345,
            time=1234567890,
            type=mt5.POSITION_TYPE_BUY,
            magic=100,
            identifier=12345,
            volume=0.1,
            price_open=1.1000,
            price_current=1.1050,
            sl=1.0950,
            tp=1.1150,
            swap=0.0,
            profit=50.0,
            symbol="EURUSD",
            comment="Test trade",
        )

        assert position.ticket == 12345
        assert position.type == mt5.POSITION_TYPE_BUY
        assert position.volume == 0.1
        assert position.price_open == 1.1000
        assert position.price_current == 1.1050
        assert position.sl == 1.0950
        assert position.tp == 1.1150
        assert position.symbol == "EURUSD"

    def test_position_array_state_initialization(self):
        """Test PositionArrayState initialization."""
        state = PositionArrayState(initial_size=10)

        assert state.count == 0
        assert state._capacity == 10
        assert len(state.id_to_index) == 0
        assert state.pos_id.shape[0] == 10
        assert state.volume.shape[0] == 10

    def test_position_array_state_add_position(self):
        """Test adding a position to PositionArrayState."""
        state = PositionArrayState(initial_size=4)

        position = PositionInfoSimulator(
            ticket=100,
            type=mt5.POSITION_TYPE_BUY,
            volume=0.5,
            price_open=1.2000,
            price_current=1.2050,
            sl=1.1900,
            tp=1.2200,
            symbol="GBPUSD",
        )

        symbol_params = {
            "contract_size": 100000.0,
            "tick_size": 0.00001,
            "tick_value": 1.0,
            "margin_mode": 0.0,
            "leverage": 100.0,
        }

        state.add_or_update(
            pos_id=100, pos_data=position, symbol_params=symbol_params, leverage=100.0
        )

        assert state.count == 1
        assert state.id_to_index[100] == 0
        assert state.pos_id[0] == 100
        assert state.volume[0] == 0.5
        assert state.price_open[0] == 1.2000
        assert state.price_current[0] == 1.2050
        assert state.sl[0] == 1.1900
        assert state.tp[0] == 1.2200
        assert state.direction[0] == 1  # Buy = 1
        assert state.symbols[0] == "GBPUSD"


class TestPnLCalculations:
    """Test profit and loss calculations."""

    def test_numba_position_update_buy_profit(self):
        """Test PnL calculation for profitable buy position."""
        # Setup arrays for one buy position
        current_prices = np.array([1.2050], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([1], dtype=np.int8)  # Buy
        sl = np.array([1.1900], dtype=np.float64)
        tp = np.array([1.2200], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        # Profit = (1.2050 - 1.2000) / 0.00001 * 1.0 * 0.1 = 50.0
        assert profit[0] == pytest.approx(50.0, rel=1e-6)
        assert not sl_hit[0]
        assert not tp_hit[0]

    def test_numba_position_update_sell_profit(self):
        """Test PnL calculation for profitable sell position."""
        # Setup arrays for one sell position
        current_prices = np.array([1.1950], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([-1], dtype=np.int8)  # Sell
        sl = np.array([1.2100], dtype=np.float64)
        tp = np.array([1.1800], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        # Profit = (1.2000 - 1.1950) * -1 / 0.00001 * 1.0 * 0.1 = 50.0
        assert profit[0] == pytest.approx(50.0, rel=1e-6)
        assert not sl_hit[0]
        assert not tp_hit[0]

    def test_numba_position_update_buy_loss(self):
        """Test PnL calculation for losing buy position."""
        current_prices = np.array([1.1950], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([1], dtype=np.int8)  # Buy
        sl = np.array([1.1900], dtype=np.float64)
        tp = np.array([1.2200], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        # Loss = (1.1950 - 1.2000) / 0.00001 * 1.0 * 0.1 = -50.0
        assert profit[0] == pytest.approx(-50.0, rel=1e-6)
        assert not sl_hit[0]
        assert not tp_hit[0]

    def test_margin_calculation_forex(self):
        """Test margin calculation for forex positions."""
        current_prices = np.array([1.2000], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([1.0], dtype=np.float64)
        direction = np.array([1], dtype=np.int8)
        sl = np.array([0.0], dtype=np.float64)
        tp = np.array([0.0], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)  # Forex mode
        leverage = np.array([100.0], dtype=np.float64)

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

        # Margin = (volume * contract_size) / leverage = (1.0 * 100000) / 100 = 1000.0
        assert margin[0] == pytest.approx(1000.0, rel=1e-6)


class TestPositionUpdates:
    """Test position update operations."""

    def test_update_position_price(self):
        """Test updating position current price."""
        state = PositionArrayState(initial_size=4)

        position = PositionInfoSimulator(
            ticket=200,
            type=mt5.POSITION_TYPE_BUY,
            volume=0.5,
            price_open=1.3000,
            price_current=1.3000,
            sl=1.2900,
            tp=1.3200,
            symbol="USDCAD",
        )

        symbol_params = {
            "contract_size": 100000.0,
            "tick_size": 0.00001,
            "tick_value": 1.0,
            "margin_mode": 0.0,
            "leverage": 50.0,
        }

        state.add_or_update(
            pos_id=200, pos_data=position, symbol_params=symbol_params
        )

        # Update price
        position.price_current = 1.3100
        state.add_or_update(
            pos_id=200, pos_data=position, symbol_params=symbol_params
        )

        assert state.count == 1  # Still one position
        assert state.price_current[0] == 1.3100

    def test_update_sl_tp(self):
        """Test updating stop loss and take profit."""
        state = PositionArrayState(initial_size=4)

        position = PositionInfoSimulator(
            ticket=300,
            type=mt5.POSITION_TYPE_SELL,
            volume=0.2,
            price_open=1.1500,
            sl=1.1600,
            tp=1.1300,
            symbol="EURUSD",
        )

        state.add_or_update(pos_id=300, pos_data=position)

        # Update SL/TP
        state.update_sl_tp(pos_id=300, sl=1.1550, tp=1.1250)

        assert state.sl[0] == 1.1550
        assert state.tp[0] == 1.1250

    def test_update_volume_margin(self):
        """Test updating position volume and margin."""
        state = PositionArrayState(initial_size=4)

        position = PositionInfoSimulator(
            ticket=400, type=mt5.POSITION_TYPE_BUY, volume=1.0, symbol="USDJPY"
        )

        state.add_or_update(pos_id=400, pos_data=position)

        # Update volume and margin (simulating partial close)
        state.update_volume_margin(pos_id=400, volume=0.5, margin=500.0)

        assert state.volume[0] == 0.5
        assert state.margin_required[0] == 500.0

    def test_remove_position(self):
        """Test removing a position from state."""
        state = PositionArrayState(initial_size=4)

        # Add two positions
        pos1 = PositionInfoSimulator(ticket=501, volume=0.1, symbol="EURUSD")
        pos2 = PositionInfoSimulator(ticket=502, volume=0.2, symbol="GBPUSD")

        state.add_or_update(pos_id=501, pos_data=pos1)
        state.add_or_update(pos_id=502, pos_data=pos2)

        assert state.count == 2

        # Remove first position
        state.remove(pos_id=501)

        assert state.count == 1
        assert 501 not in state.id_to_index
        assert 502 in state.id_to_index

    def test_rebuild_from_positions(self):
        """Test rebuilding arrays from positions dictionary."""
        state = PositionArrayState(initial_size=4)

        positions = {
            601: PositionInfoSimulator(ticket=601, volume=0.1, symbol="EURUSD"),
            602: PositionInfoSimulator(ticket=602, volume=0.2, symbol="GBPUSD"),
            603: PositionInfoSimulator(ticket=603, volume=0.3, symbol="USDJPY"),
        }

        state.rebuild_from_positions(positions)

        assert state.count == 3
        assert 601 in state.id_to_index
        assert 602 in state.id_to_index
        assert 603 in state.id_to_index


class TestSLTPHits:
    """Test stop loss and take profit hit detection."""

    def test_buy_stop_loss_hit(self):
        """Test detecting SL hit on buy position."""
        current_prices = np.array([1.1900], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([1], dtype=np.int8)  # Buy
        sl = np.array([1.1950], dtype=np.float64)
        tp = np.array([1.2200], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        assert sl_hit[0]  # SL was hit
        assert not tp_hit[0]

    def test_buy_take_profit_hit(self):
        """Test detecting TP hit on buy position."""
        current_prices = np.array([1.2250], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([1], dtype=np.int8)  # Buy
        sl = np.array([1.1900], dtype=np.float64)
        tp = np.array([1.2200], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        assert not sl_hit[0]
        assert tp_hit[0]  # TP was hit

    def test_sell_stop_loss_hit(self):
        """Test detecting SL hit on sell position."""
        current_prices = np.array([1.2100], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([-1], dtype=np.int8)  # Sell
        sl = np.array([1.2050], dtype=np.float64)
        tp = np.array([1.1800], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        assert sl_hit[0]  # SL was hit
        assert not tp_hit[0]

    def test_sell_take_profit_hit(self):
        """Test detecting TP hit on sell position."""
        current_prices = np.array([1.1750], dtype=np.float64)
        price_open = np.array([1.2000], dtype=np.float64)
        volume = np.array([0.1], dtype=np.float64)
        direction = np.array([-1], dtype=np.int8)  # Sell
        sl = np.array([1.2100], dtype=np.float64)
        tp = np.array([1.1800], dtype=np.float64)
        valid = np.array([True], dtype=np.bool_)
        contract_size = np.array([100000.0], dtype=np.float64)
        tick_size = np.array([0.00001], dtype=np.float64)
        tick_value = np.array([1.0], dtype=np.float64)
        margin_mode = np.array([0.0], dtype=np.float64)
        leverage = np.array([100.0], dtype=np.float64)

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

        assert not sl_hit[0]
        assert tp_hit[0]  # TP was hit


class TestArrayCapacityManagement:
    """Test dynamic array growth and capacity management."""

    def test_array_growth(self):
        """Test that arrays grow when capacity is exceeded."""
        state = PositionArrayState(initial_size=2)

        assert state._capacity == 2

        # Add 3 positions, should trigger growth
        for i in range(3):
            pos = PositionInfoSimulator(ticket=700 + i, volume=0.1, symbol="EURUSD")
            state.add_or_update(pos_id=700 + i, pos_data=pos)

        assert state.count == 3
        assert state._capacity >= 3  # Should have grown
        assert state.pos_id.shape[0] == state._capacity

    def test_clear(self):
        """Test clearing all positions from state."""
        state = PositionArrayState(initial_size=4)

        # Add positions
        for i in range(3):
            pos = PositionInfoSimulator(ticket=800 + i, volume=0.1, symbol="EURUSD")
            state.add_or_update(pos_id=800 + i, pos_data=pos)

        assert state.count == 3

        # Clear
        state.clear()

        assert state.count == 0
        assert len(state.id_to_index) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

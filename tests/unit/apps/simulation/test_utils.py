
import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import MagicMock
from apps.simulation.utils import (
    SimulationUtilsMixin, 
    PositionArrayState, 
    SimulatorBacktestResult,
    numba_position_update
)
from apps.mt5 import get_mt5_api

class MockUtilsSimulator(SimulationUtilsMixin):
    def __init__(self):
        self._symbols_data = {}
        self._ticks_data = {}
        self._positions_data = {}
        self._trade_records_open = {}
        self.trade = MagicMock()
        self.trade.RequestMagic.return_value = 123
        self._account_data = MagicMock()
        self._account_data.leverage = 100
        self._simulator = MagicMock()
    
    def _to_epoch_seconds(self, t):
        if hasattr(t, "timestamp"): return int(t.timestamp())
        return int(t)

def test_normalize_pending_type():
    sim = MockUtilsSimulator()
    mt5 = get_mt5_api()
    # Use actual MT5 constants
    assert sim._normalize_pending_type(mt5.ORDER_TYPE_BUY_LIMIT) == "buy limit"
    assert sim._normalize_pending_type("Buy_Limit") == "buy limit"
    
def test_pending_action():
    sim = MockUtilsSimulator()
    assert sim._pending_action("Buy Limit") == "buy"
    assert sim._pending_action("Sell Stop") == "sell"

def test_normalize_expiry_date():
    sim = MockUtilsSimulator()
    dt = datetime(2023, 1, 1, 12, 0, 0)
    assert sim._normalize_expiry_date(dt) == dt
    
    dt_tz = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    res = sim._normalize_expiry_date(dt_tz)
    assert res.tzinfo is None # Should strip tz

def test_validate_pending_distance():
    sim = MockUtilsSimulator()
    mock_symbol = MagicMock()
    mock_symbol.trade_stops_level = 10
    mock_symbol.point = 0.0001
    sim._symbols_data["EURUSD"] = mock_symbol
    
    mock_tick = MagicMock()
    mock_tick.bid = 1.1000
    mock_tick.ask = 1.1002
    sim._ticks_data["EURUSD"] = mock_tick
    
    # Distance is 10 * 0.0001 = 0.001
    
    # Buy Limit at 1.0995 (Bid 1.1000). Diff 0.0005 < 0.001. Too close?
    # Logic: abs(open - bid). 
    valid, msg = sim._validate_pending_distance("buy limit", "EURUSD", 1.0995)
    assert valid is False
    assert "too close" in msg
    
    # Buy Limit at 1.0900. Diff 0.01. OK.
    valid, msg = sim._validate_pending_distance("buy limit", "EURUSD", 1.0900)
    assert valid is True

def test_update_position_entry():
    sim = MockUtilsSimulator()
    sim._positions_data[123] = MagicMock()
    
    sim._update_position_entry(
        action="buy",
        symbol="EURUSD",
        volume=1.0,
        price=1.1,
        sl=1.0,
        tp=1.2,
        comment="test",
        margin_required=100.0,
        open_time=datetime.now(),
        pos_id=123
    )
    
    pos = sim._positions_data[123]
    assert pos.symbol == "EURUSD"
    assert pos.volume == 1.0
    assert pos.magic == 123

def test_position_array_state():
    state = PositionArrayState()
    
    class PosData:
        symbol = "EURUSD"
        type = 0 # BUY
        volume = 1.0
        price_open = 1.1
        sl = 1.05
        tp = 1.15
        
    state.add_or_update(1, PosData())
    assert state.count == 1
    assert state.symbols[0] == "EURUSD"
    assert state.volume[0] == 1.0
    
    state.remove(1)
    assert state.count == 0

def test_numba_position_update():
    # Setup arrays
    count = 1
    current_prices = np.array([1.1100], dtype=np.float64)
    price_open = np.array([1.1000], dtype=np.float64)
    volume = np.array([1.0], dtype=np.float64)
    direction = np.array([1], dtype=np.float64) # Buy
    sl = np.array([1.0900], dtype=np.float64)
    tp = np.array([1.1200], dtype=np.float64)
    valid = np.array([True], dtype=np.bool_)
    contract_size = np.array([100000.0], dtype=np.float64)
    tick_size = np.array([0.00001], dtype=np.float64)
    tick_value = np.array([1.0], dtype=np.float64)
    margin_mode = np.array([0.0], dtype=np.float64)
    leverage = np.array([100.0], dtype=np.float64)
    
    profit, margin, sl_hit, tp_hit = numba_position_update(
        current_prices, price_open, volume, direction, sl, tp, valid,
        contract_size, tick_size, tick_value, margin_mode, leverage
    )
    
    # Profit: (1.1100 - 1.1000) / 0.00001 * 1.0 * 1.0 = 1000.0
    assert np.isclose(profit[0], 1000.0)
    assert not sl_hit[0]
    assert not tp_hit[0]
    
    # SL Hit scenario
    current_prices[0] = 1.0800
    profit, margin, sl_hit, tp_hit = numba_position_update(
        current_prices, price_open, volume, direction, sl, tp, valid,
        contract_size, tick_size, tick_value, margin_mode, leverage
    )
    assert sl_hit[0]

def test_simulator_backtest_result():
    sim = MagicMock()
    sim._completed_trades = []
    sim._initial_balance = 10000
    sim._account_data.balance = 10100
    
    result = SimulatorBacktestResult(sim)
    assert result.total_return == 100.0
    assert result.total_return_pct == 1.0
    
    summary = result.summary()
    assert summary["total_return_pct"] == 1.0

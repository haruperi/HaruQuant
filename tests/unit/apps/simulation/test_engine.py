
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from apps.simulation.engine import SimulationEngine, _support_point_split, _linspace, _expand_ticks, _clamp

def test_support_point_split():
    assert _support_point_split(11) == (3, 5, 3)
    assert _support_point_split(3) == (1, 1, 1)
    assert _support_point_split(2) == (0, 2, 0)

def test_linspace():
    assert _linspace(0, 10, 0) == []
    assert _linspace(0, 10, 1) == [5.0]
    assert len(_linspace(0, 10, 9)) == 9

def test_clamp():
    assert _clamp(5, 0, 10) == 5
    assert _clamp(-5, 0, 10) == 0
    assert _clamp(15, 0, 10) == 10

def test_expand_ticks():
    points = [1.0, 1.1]
    expanded = _expand_ticks(points, 5, 0.001)
    # Result should have 5 points
    assert len(expanded) == 5
    assert expanded[0] == 1.0
    assert expanded[-1] == 1.1

class MockEngine(SimulationEngine):
    def __init__(self):
        self._ticks_data = {}
        self._positions_data = {}
        self._symbols_data = {}
        self._simulator = MagicMock()
        self._account_data = MagicMock()
        self._account_data.balance = 10000
        self.trade = MagicMock()
        self.open_position = MagicMock()
        self.close_position = MagicMock()
        self._ensure_trade_record = MagicMock()
        self._update_trade_tracker = MagicMock()
        self._calc_profit = MagicMock(return_value=10.0)
        self._calc_margin = MagicMock(return_value=5.0)
        self.monitor_pending_orders = MagicMock()
        self.monitor_account = MagicMock()
        
        # Mixin helpers
        self._to_datetime = MagicMock(side_effect=lambda x: x)
        self._pip_size = MagicMock(return_value=0.0001)

def test_ensure_tick():
    engine = MockEngine()
    tick = engine._ensure_tick("EURUSD")
    assert tick is not None
    assert "EURUSD" in engine._ticks_data

def test_on_tick():
    engine = MockEngine()
    engine._on_tick(
        symbol="EURUSD",
        tick_time="2023-01-01",
        bid=1.1,
        ask=1.2,
        last=1.15
    )
    
    assert engine._ticks_data["EURUSD"].bid == 1.1
    engine.monitor_pending_orders.assert_called()
    engine.monitor_account.assert_called()

def test_monitor_positions():
    engine = MockEngine()
    engine._positions_data[1] = MagicMock(
        symbol="EURUSD",
        type=0, # BUY
        price_open=1.0,
        volume=1.0,
        sl=0.0,
        tp=0.0
    )
    engine._ticks_data["EURUSD"] = MagicMock(bid=1.1, ask=1.12)
    
    res = engine.monitor_positions()
    assert res["profit"] == 10.0 # From mock return_value

def test_monitor_positions_sl_hit():
    engine = MockEngine()
    pos = MagicMock(
        symbol="EURUSD",
        type=0, # BUY
        price_open=1.1,
        volume=1.0,
        sl=1.05,
        tp=0.0
    )
    pos._asdict.return_value = {}
    engine._positions_data[1] = pos
    
    engine._ticks_data["EURUSD"] = MagicMock(bid=1.00, ask=1.02)
    
    engine.monitor_positions()
    engine.close_position.assert_called_once()

def test_generate_ticks():
    engine = MockEngine()
    
    df = pd.DataFrame([{
        "time": "2023-01-01",
        "open": 1.0,
        "high": 1.1,
        "low": 0.9,
        "close": 1.05,
        "tick_volume": 4
    }])
    df.set_index("time", inplace=True)
    
    ticks = list(engine._generate_ticks(
        m1_data=df,
        symbol="EURUSD",
        point=0.0001,
        spread_default=10
    ))
    
    assert len(ticks) > 0
    # Last tick should match close price
    last_tick_bid = ticks[-1][1]
    assert last_tick_bid == 1.05

def test_m1_run():
    engine = MockEngine()
    df = pd.DataFrame([{
        "time": "2023-01-01",
        "open": 1.0,
        "high": 1.1,
        "low": 0.9,
        "close": 1.05
    }])
    df.set_index("time", inplace=True)
    
    ticks = list(engine._m1_run(
        m1_data=df,
        symbol="EURUSD",
        point=0.0001,
        spread_default=10
    ))
    
    assert len(ticks) == 4 # OHLC

def test_process_bar_signal():
    engine = MockEngine()
    
    data = pd.DataFrame([{"close": 1.1}], index=["2023-01-01"])
    strategy = MagicMock()
    strategy.get_signal.return_value = {"entry_signal": 1, "exit_signal": 0}
    
    tick = MagicMock(ask=1.1, bid=1.09)
    validator = MagicMock()
    
    engine._process_bar_signal(
        data=data,
        idx=0,
        strategy=strategy,
        symbol="EURUSD",
        volume=0.1,
        tick=tick,
        validator=validator,
        verbose=False
    )
    
    # Verify open_position was called for buy signal
    assert engine.open_position.called
    call_args = engine.open_position.call_args
    assert call_args[0][0] == "buy"
    assert call_args[0][1] == "EURUSD"


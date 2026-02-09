
import pytest
import time
from datetime import datetime
from unittest.mock import MagicMock
from apps.simulation.records import TradeRecord, TradeRecordMixin

class MockSimulator(TradeRecordMixin):
    def __init__(self):
        self._symbols_data = {}
        self._ticks_data = {}
        self._trade_records_open = {}
        self._account_data = MagicMock()
        self._account_data.balance = 10000.0
        self._account_data.equity = 10000.0
        self._account_data.margin = 0.0
        self._account_data.margin_free = 10000.0
        self._trade_trackers = {}
        self.trade = MagicMock()
        self.trade.RequestMagic.return_value = 123456
        self.mt5_client = MagicMock()
        self.mt5_client.order_calc_profit.return_value = 10.0

def test_trade_record_dataclass():
    record = TradeRecord(ticket=1)
    assert record.ticket == 1
    assert record.type == "buy" # Default

def test_trade_record_mixin_conversions():
    sim = MockSimulator()
    
    # _to_epoch_seconds
    now = time.time()
    assert abs(sim._to_epoch_seconds(now) - int(now)) <= 1
    assert abs(sim._to_epoch_seconds(datetime.fromtimestamp(now)) - int(now)) <= 1
    
    # _to_datetime
    dt = sim._to_datetime(now)
    assert isinstance(dt, datetime)
    assert abs(dt.timestamp() - now) <= 1

def test_pip_size_calculation():
    sim = MockSimulator()
    mock_symbol = MagicMock()
    mock_symbol.point = 0.0001
    sim._symbols_data["EURUSD"] = mock_symbol
    
    assert sim._pip_size("EURUSD") == 0.001
    # Test cache
    sim._pip_size_cache["EURUSD"] = 0.002
    assert sim._pip_size("EURUSD") == 0.002

def test_ensure_trade_record():
    sim = MockSimulator()
    mock_symbol = MagicMock()
    mock_symbol.point = 0.00001
    sim._symbols_data["EURUSD"] = mock_symbol
    
    tick = MagicMock()
    tick.bid = 1.1000
    tick.ask = 1.1002
    sim._ticks_data["EURUSD"] = tick
    
    sim._ensure_trade_record(
        pos_id=1,
        action="buy",
        symbol="EURUSD",
        volume=0.1,
        price=1.1002,
        sl=1.0900,
        tp=1.1200,
        comment="test",
        requested_entry_price=1.1002,
        open_time=datetime.now()
    )
    
    assert 1 in sim._trade_records_open
    record = sim._trade_records_open[1]
    assert record.symbol == "EURUSD"
    assert record.initial_risk_pips > 0

    # Ensure duplicate call doesn't overwrite (logic check)
    sim._trade_records_open[1].comment = "modified"
    sim._ensure_trade_record(
        pos_id=1, action="buy", symbol="EURUSD", volume=0.1, price=1.1, sl=0, tp=0, 
        comment="new", requested_entry_price=1.1, open_time=datetime.now()
    )
    assert sim._trade_records_open[1].comment == "modified"

def test_update_trade_tracker():
    sim = MockSimulator()
    sim._pip_size = MagicMock(return_value=0.0001)
    
    sim._trade_trackers[1] = {
        "bars_in_trade": 0,
        "mfe_usd": 0.0,
        "mae_usd": 0.0,
        "mfe_pips": 0.0,
        "mae_pips": 0.0,
    }
    
    # Buy trade, price moves up
    sim._update_trade_tracker(
        pos_id=1,
        action="buy",
        symbol="EURUSD",
        entry_price=1.1000,
        current_price=1.1050,
        profit_usd=50.0
    )
    
    tracker = sim._trade_trackers[1]
    assert tracker["bars_in_trade"] == 1
    assert tracker["mfe_usd"] == 50.0
    assert tracker["mfe_pips"] > 0

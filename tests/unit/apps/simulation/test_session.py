
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from apps.simulation.session import SimulatorSession, _parse_time, _serialize_time

def test_time_helpers():
    assert _parse_time(None) is None
    dt = datetime(2023, 1, 1)
    assert _parse_time("2023-01-01") == dt
    
    assert _serialize_time(dt) == dt.isoformat()
    assert _serialize_time(None) == ""

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_mt5_credentials.return_value = {}
    return db

@pytest.fixture
def session(mock_db):
    config = {
        "session_name": "TestSession",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "initial_balance": 10000.0
    }
    with patch("apps.simulation.session.MT5Client"), \
         patch("apps.simulation.session.TradeSimulator"):
        sess = SimulatorSession(1, config, mock_db)
        yield sess

def test_session_init(session):
    assert session.symbol == "EURUSD"
    assert session.simulator is not None

def test_load_historical_bars(session):
    # Mock data provided in config
    session.config["bars"] = [{"time": "2023-01-01T00:00:00", "close": 1.1}]
    bars = session.load_historical_bars()
    assert len(bars) == 1
    assert session._data is not None

def test_get_bar(session):
    session.config["bars"] = [{"time": "2023-01-01T00:00:00", "close": 1.1}]
    assert session.get_bar(0)["close"] == 1.1
    assert session.get_bar(1) is None

def test_process_bar_at_index(session):
    session.config["bars"] = [{"time": "2023-01-01T00:00:00", "close": 1.1}]
    session.load_historical_bars()
    
    session.simulator._symbols_data = {"EURUSD": MagicMock(point=0.00001, spread=10)}
    session.simulator._account_data = MagicMock(balance=10000.0)
    
    res = session.process_bar_at_index(0)
    assert res["balance"] == 10000.0

def test_get_indicators(session):
    session.config["bars"] = [
        {"time": f"2023-01-01T{i}:00:00", "close": 10 + i} for i in range(20)
    ]
    session.load_historical_bars()
    session.config["indicators_enabled"] = True
    session.config["indicator_sma_enabled"] = True
    session.config["sma_period"] = 5
    
    res = session.get_indicators_at_index(10)
    assert "sma" in res

def test_execute_trade(session):
    session.config["bars"] = [{"time": "2023-01-01T00:00:00", "close": 1.1}]
    session.load_historical_bars()
    
    session.simulator.open_position.return_value = True
    session.simulator._positions_data = {}
    
    res = session.execute_trade({
        "side": "buy",
        "volume": 0.1,
        "price": 1.1
    })
    
    assert res is not None
    assert res["side"] == "buy"
    session.db.save_trade.assert_called()

def test_place_pending_order(session):
    session.config["bars"] = [{"time": "2023-01-01T00:00:00", "close": 1.1}]
    session.load_historical_bars()
    
    session.simulator.buy_limit.return_value = True
    
    res = session.place_pending_order({
        "type": "buy_limit",
        "volume": 0.1,
        "price": 1.0,
    })
    
    assert res is not None
    assert res["type"] == "buy_limit"

def test_lifecycle(session):
    session.pause()
    assert session.is_paused
    session.resume()
    assert not session.is_paused
    session.stop()
    assert not session._is_running


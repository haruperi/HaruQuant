
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import pytest
from apps.live.session import LiveTradingSession, ExecutionEngineWrapper

@pytest.fixture
def mock_mt5():
    return Mock()

@pytest.fixture
def mock_db():
    db = Mock()
    db.get_live_session.return_value = {
        "user_id": 1,
        "max_positions": 5,
        "max_total_risk_pct": 2.0,
        "max_correlation": 3
    }
    db.get_user.return_value = {"username": "testuser"}
    db.get_session_strategies.return_value = [
        {
            "strategy_id": "strat1",
            "symbols": ["EURUSD"],
            "timeframes": ["H1"],
            "strategy_type": "Trend",
            "strategy_name": "TestStrat",
            "version": "1.0",
            "strategy_params": {}
        }
    ]
    return db

@pytest.fixture
def session(mock_mt5, mock_db):
    return LiveTradingSession(1, mock_mt5, mock_db)

@pytest.mark.asyncio
async def test_session_start(session):
    with patch("apps.live.session.MultiStrategyEngine") as MockEngine:
        mock_engine_instance = MockEngine.return_value
        mock_engine_instance.initialize.return_value = True
        
        # We need to mock _run_engine_loop to avoid infinite loop or blocking
        session._run_engine_loop = AsyncMock()
        
        await session.start()
        
        MockEngine.assert_called_once()
        mock_engine_instance.initialize.assert_called_once()
        session._run_engine_loop.assert_called_once() # Should be awaited via create_task -> check if task created
        assert session._task is not None
        
        session.db.update_live_session.assert_called_with(1, status="running")

@pytest.mark.asyncio
async def test_session_stop(session):
    session.engine = Mock()
    session._task = AsyncMock()
    
    await session.stop()
    
    session.engine.stop.assert_called_once()
    session.db.update_live_session.assert_called_with(1, status="stopped")

@pytest.mark.asyncio
async def test_session_pause_resume(session):
    session.engine = Mock()
    session.engine.state_manager = Mock()
    
    await session.pause()
    session.engine.state_manager.pause.assert_called_once()
    session.db.update_live_session.assert_called_with(1, status="paused")
    
    await session.resume()
    session.engine.state_manager.resume.assert_called_once()
    session.db.update_live_session.assert_called_with(1, status="running")

def test_build_engine_config(session):
    session_data = session.db.get_live_session(1)
    config = session._build_engine_config(session_data)
    
    assert config["user_id"] == 1
    assert len(config["strategies"]) == 1
    assert config["strategies"][0]["symbol"] == "EURUSD"
    assert config["strategies"][0]["timeframe"] == "H1"

def test_get_status(session):
    session.engine = Mock()
    session.engine.get_status.return_value = {
        "portfolio": {"equity": 1000.0, "balance": 1000.0, "total_positions": 1},
        "strategies": [
            {"signals_detected": 5, "signals_executed": 2, "trades_executed": 2}
        ]
    }
    session.engine._running = True
    session.mt5_client.account_name = "Demo"
    
    status = session.get_status()
    
    assert status["status"] == "running"
    assert status["signals_detected"] == 5
    assert status["signals_approved"] == 2
    assert status["signals_rejected"] == 3 # 5-2
    assert status["active_positions"] == 1
    assert status["current_equity"] == 1000.0

@pytest.mark.asyncio
async def test_execution_engine_wrapper(session):
    session.engine = Mock()
    session.engine.trade = Mock()
    session.engine.trade.PositionClose = Mock(return_value=True)
    session.engine._get_supported_filling_mode.return_value = 1
    
    wrapper = session.execution_engine
    assert isinstance(wrapper, ExecutionEngineWrapper)
    
    # Mock position object
    # Mock position object using SimpleNamespace or class to avoid Mock weirdness
    from types import SimpleNamespace
    position = SimpleNamespace(ticket=12345, symbol="EURUSD")
    
    result = await wrapper.close_position(position)
    
    assert result is True
    # Verify called with ticket
    args, kwargs = session.engine.trade.PositionClose.call_args
    assert kwargs['ticket'] == 12345

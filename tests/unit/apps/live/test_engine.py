
from unittest.mock import Mock, patch, MagicMock
import pytest
from apps.live.engine import MultiStrategyEngine, StrategyInstance

@pytest.fixture
def mock_config():
    return {
        "mt5": {"login": 123, "password": "pwd", "server": "srv"},
        "portfolio": {},
        "strategies": [
            {"name": "Strat1", "symbol": "EURUSD", "timeframe": "H1", "strategy_type": "TrendFollowing"}
        ],
        "logging": {"dir": "logs"},
        "state": {"file": "state.json"},
        "notifications": {"enable_email": False}
    }

@pytest.fixture
def engine(mock_config):
    with patch("apps.live.engine.get_mt5_api"), \
         patch("apps.live.engine.MT5Client"), \
         patch("apps.live.engine.Trade"), \
         patch("apps.live.engine.AccountInfo"), \
         patch("apps.live.engine.PortfolioManager"), \
         patch("apps.live.engine.StateManager"), \
         patch("apps.live.engine.LiveTradingNotifier"), \
         patch("pathlib.Path.mkdir"):
        
        eng = MultiStrategyEngine(config=mock_config)
        eng.client = Mock() # Ensure client is mocked
        return eng

def test_initialization(engine):
    # Mock internal methods to isolate init login
    engine._initialize_strategy = Mock(return_value=True)
    engine.portfolio_manager = Mock()
    engine.portfolio_manager.get_portfolio_summary.return_value = {"total_positions": 0, "profit": 0}
    
    assert engine.initialize() is True
    assert engine._initialized is True
    assert engine.client is not None

def test_initialize_strategy_success(engine):
    config = {"name": "Test", "symbol": "EURUSD", "timeframe": "M1", "strategy_type": "TrendFollowing"}
    
    # Mock overrides
    engine.client = Mock()
    engine.trade = Mock()
    
    with patch("apps.live.engine.TrendFollowingStrategy") as MockStrat, \
         patch("apps.live.engine.BarMonitor") as MockBar, \
         patch("apps.live.engine.SignalProcessor") as MockSig, \
         patch("apps.live.engine.PositionManager") as MockPos, \
         patch("apps.live.engine.SafetyChecker") as MockSafe, \
         patch("apps.live.engine.TradeExecutor") as MockExec, \
         patch("apps.live.engine.SymbolInfo", return_value=Mock(volume_step=0.01)): # Fix SymbolInfo mock
            
            MockSig.return_value.initialize.return_value = True
            MockBar.return_value.get_historical_data.return_value = Mock(empty=False)

            # We need to ensure _setup_signal_processor returns something
            engine._setup_signal_processor = Mock(return_value=MockSig.return_value)
            
            # _create_trade_executor needs to return something
            engine._create_trade_executor = Mock(return_value=MockExec.return_value)
            engine._create_safety_checker = Mock(return_value=MockSafe.return_value)
            
            success = engine._initialize_strategy(config)
            
            assert success is True
            assert len(engine.strategies) == 1
            assert engine.strategies[0].name == "Test"

def test_run_iteration(engine):
    engine.state_manager = Mock()
    engine.state_manager.is_enabled.return_value = True
    engine.state_manager.is_paused.return_value = False
    
    engine.portfolio_manager = Mock()
    
    strategy = Mock()
    engine.strategies = [strategy]
    
    engine._process_strategy = Mock()
    engine._export_status = Mock()
    
    with patch("time.sleep"):
        engine._run_iteration()
        
    engine.portfolio_manager.refresh_all_positions.assert_called_once()
    engine._process_strategy.assert_called_with(strategy)
    engine.state_manager.update_last_run.assert_called_once()

def test_process_strategy_no_new_bar(engine):
    strategy = Mock()
    strategy.bar_monitor.check_new_bar.return_value = False
    
    engine._process_strategy(strategy)
    
    strategy.signal_processor.update_with_new_bar.assert_not_called()

def test_process_strategy_with_signal(engine):
    strategy = Mock()
    strategy.bar_monitor.check_new_bar.return_value = True
    strategy.bar_monitor.get_last_closed_bar.return_value = Mock()
    
    strategy.signal_processor.update_with_new_bar.return_value = {"signal": "buy"}
    
    engine._handle_signal = Mock()
    
    engine._process_strategy(strategy)
    
    engine._handle_signal.assert_called()

def test_handle_signal(engine):
    strategy = MagicMock()
    strategy.config = {}
    strategy.symbol = "EURUSD"
    strategy.name = "Test"
    signal = {"signal": "buy"}
    
    # Mock validation
    engine.portfolio_manager = Mock()
    engine.portfolio_manager.can_open_position.return_value = (True, "OK")
    
    strategy.safety_checker.check_all.return_value = (True, "OK")
    
    strategy.trade_executor.execute_signal.return_value = (True, "Order executed")
    strategy.trades_executed = 0
    strategy.trades_failed = 0
    
    engine._handle_signal(strategy, signal)
    
    strategy.trade_executor.execute_signal.assert_called()
    assert strategy.trades_executed == 1

def test_normalize_signal(engine):
    # Case 1: Standard
    sig = {"signal": "buy", "price": 1.1}
    norm = engine._normalize_signal(sig)
    assert norm["signal"] == "buy"
    assert norm["entry_price"] == 1.1
    
    # Case 2: Numeric signal
    sig = {"entry_signal": 1, "exit_signal": 0}
    norm = engine._normalize_signal(sig)
    assert norm["signal"] == "buy"
    
    sig = {"entry_signal": -1}
    norm = engine._normalize_signal(sig)
    assert norm["signal"] == "sell"
    
    # Case 3: Exit numeric
    sig = {"exit_signal": 1}
    norm = engine._normalize_signal(sig)
    assert norm["signal"] == "close buy"

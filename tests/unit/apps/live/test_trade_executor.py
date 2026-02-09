
from unittest.mock import Mock, call, patch
import pytest
from apps.live.trade_executor import TradeExecutor

@pytest.fixture
def mock_trade():
    trade = Mock()
    trade.ResultRetcode.return_value = 10009 # DONE
    trade.ResultOrder.return_value = 123
    trade.ResultDeal.return_value = 456
    trade.ResultPrice.return_value = 1.12345
    trade.ResultVolume.return_value = 0.1
    trade.ResultRetcodeDescription.return_value = "Done"
    trade.ResultComment.return_value = "Comment"
    return trade

@pytest.fixture
def mock_symbol_info():
    info = Mock()
    info.Ask.return_value = 1.1000
    info.Bid.return_value = 1.0900
    return info

@pytest.fixture
def mock_position_manager():
    return Mock()

@pytest.fixture
def executor(mock_trade, mock_symbol_info, mock_position_manager):
    return TradeExecutor(
        trade=mock_trade,
        symbol_info=mock_symbol_info,
        position_manager=mock_position_manager,
        symbol="EURUSD",
        volume=0.1,
        filling_mode=1,
        max_retries=2
    )

def test_execute_signal_unknown(executor):
    success, msg = executor.execute_signal({"signal": "unknown"})
    assert success is False
    assert "Unknown signal type" in msg

def test_execute_buy_success(executor, mock_trade):
    mock_trade.Buy.return_value = True
    
    signal = {"signal": "buy", "time": None, "stop_loss": 1.09, "take_profit": 1.11}
    success, msg = executor.execute_signal(signal)
    
    assert success is True
    assert "order executed successfully" in msg
    mock_trade.Buy.assert_called_once()
    mock_trade.SetTypeFilling.assert_called_with(1)

def test_execute_sell_success(executor, mock_trade):
    mock_trade.Sell.return_value = True
    
    signal = {"signal": "sell", "time": None}
    success, msg = executor.execute_signal(signal)
    
    assert success is True
    mock_trade.Sell.assert_called_once()

def test_execute_close_positions(executor, mock_position_manager, mock_trade):
    mock_position_manager.get_positions_to_close.return_value = [100, 101]
    mock_trade.PositionClose.return_value = True
    
    signal = {"signal": "close buy", "time": None}
    success, msg = executor.execute_signal(signal)
    
    assert success is True
    assert "Successfully closed 2" in msg
    assert mock_trade.PositionClose.call_count == 2

def test_execute_retry_logic(executor, mock_trade):
    # First attempt fails with transient error (Requote 10004)
    # Second attempt succeeds
    
    mock_trade.Buy.side_effect = [False, True]
    mock_trade.ResultRetcode.side_effect = [10004, 10009]
    mock_trade.ResultRetcodeDescription.return_value = "Requote"
    
    # We need to mock get_mt5_api to return codes
    with patch("apps.live.trade_executor.get_mt5_api") as mock_mt5_mod:
        mock_mt5_mod.return_value.TRADE_RETCODE_REQUOTE = 10004
        # Need to ensure 'getattr' works on this mock or configure it
        
        signal = {"signal": "buy", "time": None}
        success, msg = executor.execute_signal(signal)
        
        assert success is True
        assert mock_trade.Buy.call_count == 2

def test_execute_retry_exhausted(executor, mock_trade):
    # All attempts fail with transient error
    mock_trade.Buy.return_value = False
    mock_trade.ResultRetcode.return_value = 10004 # Requote
    
    with patch("apps.live.trade_executor.get_mt5_api") as mock_mt5_mod:
        mock_mt5_mod.return_value.TRADE_RETCODE_REQUOTE = 10004
        
        signal = {"signal": "buy", "time": None}
        success, msg = executor.execute_signal(signal)
        
        assert success is False
        assert "order failed after 2 attempts" in msg or "Requote" in msg or "Done" in msg
        # Actually message is: "BUY order failed | Retcode: Done | Comment: Comment"
        # We should check if retcode description is in message
        assert "Done" in msg
        assert mock_trade.Buy.call_count == 2

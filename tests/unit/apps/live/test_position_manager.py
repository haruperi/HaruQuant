
from unittest.mock import Mock, call
import pytest
from apps.live.position_manager import PositionManager

@pytest.fixture
def mock_client():
    return Mock()

@pytest.fixture
def manager(mock_client):
    return PositionManager(mock_client, magic_number=123)

def test_refresh_positions_empty(manager, mock_client):
    mock_client.positions_get.return_value = []
    manager.refresh_positions()
    assert manager._positions == []

def test_refresh_positions_filtered(manager, mock_client):
    pos1 = Mock()
    pos1.magic = 123
    pos1.ticket = 1
    pos1.symbol = "EURUSD"
    
    pos2 = Mock()
    pos2.magic = 456
    pos2.ticket = 2
    pos2.symbol = "GBPUSD"
    
    pos3 = Mock()
    pos3.magic = 123
    pos3.ticket = 3
    pos3.symbol = "USDJPY"
    
    # positions_get can require tuple or kwargs. Return list in any case.
    mock_client.positions_get.return_value = [pos1, pos2, pos3]
    manager.refresh_positions()
    
    # Verify filtering
    assert len(manager._positions) == 2
    assert manager._positions[0] == pos1
    assert manager._positions[1] == pos3

def test_get_positions_by_type(manager, mock_client):
    pos_buy = Mock(magic=123, type=0, ticket=1) # 0=Buy
    pos_sell = Mock(magic=123, type=1, ticket=2) # 1=Sell
    
    mock_client.positions_get.return_value = [pos_buy, pos_sell]
    manager.refresh_positions()
    
    buys = manager.get_positions_by_type("buy")
    assert len(buys) == 1
    assert buys[0] == pos_buy
    
    sells = manager.get_positions_by_type("sell")
    assert len(sells) == 1
    assert sells[0] == pos_sell

def test_should_allow_entry(manager, mock_client):
    manager._positions = [Mock(), Mock()] # 2 positions
    
    assert manager.should_allow_entry(max_positions=3) is True
    assert manager.should_allow_entry(max_positions=2) is False

def test_close_position_success(manager):
    ticket = 12345
    symbol = "EURUSD"
    pos = Mock(ticket=ticket, symbol=symbol)
    manager._positions = [pos]
    
    manager.trade = Mock()
    manager.trade.PositionClose.return_value = True
    
    assert manager.close_position(ticket) is True
    manager.trade.PositionClose.assert_called_with(symbol=symbol, ticket=ticket)

def test_close_position_fail(manager):
    ticket = 12345
    symbol = "EURUSD"
    pos = Mock(ticket=ticket, symbol=symbol)
    manager._positions = [pos]
    
    manager.trade = Mock()
    manager.trade.PositionClose.return_value = False
    
    assert manager.close_position(ticket) is False

def test_close_positions_by_symbol(manager):
    pos1 = Mock(ticket=1, symbol="EURUSD", magic=123)
    pos2 = Mock(ticket=2, symbol="GBPUSD", magic=123)
    pos3 = Mock(ticket=3, symbol="EURUSD", magic=123)
    
    manager._positions = [pos1, pos2, pos3]
    manager.client.positions_get.return_value = manager._positions # Mock refresh
    
    manager.trade = Mock()
    manager.trade.PositionClose.return_value = True
    
    count = manager.close_positions_by_symbol("EURUSD")
    assert count == 2
    
    # Check calls
    calls = [call(symbol="EURUSD", ticket=1), call(symbol="EURUSD", ticket=3)]
    manager.trade.PositionClose.assert_has_calls(calls, any_order=True)

def test_has_position_for_symbol(manager):
    pos = Mock(symbol="EURUSD")
    manager._positions = [pos]
    
    assert manager.has_position_for_symbol("EURUSD") is True
    assert manager.has_position_for_symbol("GBPUSD") is False

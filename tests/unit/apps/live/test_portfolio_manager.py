
from unittest.mock import Mock
from collections import namedtuple
import pytest
from apps.live.portfolio_manager import PortfolioManager

@pytest.fixture
def mock_client():
    return Mock()

@pytest.fixture
def mock_account():
    account = Mock()
    account.Balance.return_value = 10000.0
    account.Margin.return_value = 1000.0
    return account

@pytest.fixture
def manager(mock_client, mock_account):
    return PortfolioManager(
        client=mock_client,
        account=mock_account,
        max_total_positions=10,
        max_positions_per_symbol=3,
        max_portfolio_risk_percent=20.0,
        max_correlated_positions=5
    )

def test_refresh_all_positions(manager, mock_client):
    pos1 = Mock(symbol="EURUSD")
    pos2 = Mock(symbol="GBPUSD")
    pos3 = Mock(symbol="EURUSD")
    
    mock_client.positions_get.return_value = [pos1, pos2, pos3]
    manager.refresh_all_positions()
    
    assert len(manager._all_positions) == 3
    assert len(manager._positions_by_symbol["EURUSD"]) == 2
    assert manager._positions_by_currency["EUR"] == 2
    assert manager._positions_by_currency["USD"] == 3 # EURUSD + GBPUSD + EURUSD

def test_can_open_position_limits(manager):
    # Mock positions
    manager._all_positions = [Mock()] * 10
    allowed, reason = manager.can_open_position("EURUSD", "strat", 0.1, "buy")
    assert allowed is False
    assert "Portfolio position limit reached" in reason
    
    manager._all_positions = [Mock()] * 9
    allowed, reason = manager.can_open_position("EURUSD", "strat", 0.1, "buy")
    assert allowed is True # Limits OK, risk needs check

def test_can_open_position_symbol_limit(manager):
    manager._positions_by_symbol["EURUSD"] = [Mock()] * 3
    allowed, reason = manager.can_open_position("EURUSD", "strat", 0.1, "buy")
    assert allowed is False
    assert "Symbol position limit reached" in reason

def test_check_portfolio_risk(manager, mock_account):
    # Balance 10000, margin 1000. Risk = 10%
    # Try adding, estimate new margin = 1000 * 1.05 = 1050 => 10.5% risk
    # Max risk 20%. Should pass.
    
    passed, reason = manager._check_portfolio_risk("EURUSD", 0.1)
    assert passed is True
    
    # Simulate high existing risk
    mock_account.Margin.return_value = 2000.0 # 20%
    # New margin ~2100 => 21% > 20%
    passed, reason = manager._check_portfolio_risk("EURUSD", 0.1)
    assert passed is False
    assert "Portfolio risk limit exceeded" in reason

def test_check_correlation_exposure(manager):
    # EUR group
    manager._positions_by_symbol["EURUSD"] = [Mock()] * 3
    manager._positions_by_symbol["EURJPY"] = [Mock()] * 2
    # Total 5 in EUR group. Max 5. Next one should fail.
    
    passed, reason = manager._check_correlation_exposure("EURAUD") # Also in EUR group
    assert passed is False
    assert "Correlation limit reached" in reason
    
    passed, reason = manager._check_correlation_exposure("EURAUD")
    
    # Reduce count
    manager._positions_by_symbol["EURJPY"] = [Mock()] # Total 4
    passed, reason = manager._check_correlation_exposure("EURAUD")
    assert passed is True

def test_check_opposing_positions(manager):
    # Patch OrderType to ensure values match our mocks
    from unittest.mock import patch
    with patch("apps.live.portfolio_manager.OrderType") as MockOrderType:
        MockOrderType.BUY.value = 0
        MockOrderType.SELL.value = 1
        
        manager._positions_by_symbol["EURUSD"] = [Mock(type=0)] # Buy
        
        # Try Sell
        passed, reason = manager._check_opposing_positions("EURUSD", "sell")
        assert passed is True
        assert "Warning: Opening SELL" in reason
        
        # Try Buy
        passed, reason = manager._check_opposing_positions("EURUSD", "buy")
        assert passed is True
        assert "No opposing positions" in reason

def test_get_portfolio_summary(manager, mock_account):
    manager._all_positions = [Mock(type=0), Mock(type=1)]
    manager.get_portfolio_summary()
    mock_account.Balance.assert_called()

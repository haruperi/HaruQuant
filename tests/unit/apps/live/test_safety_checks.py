
from unittest.mock import Mock, MagicMock
import pytest
from apps.live.safety_checks import SafetyChecker

@pytest.fixture
def mock_client():
    client = Mock()
    client.is_connected.return_value = True
    return client

@pytest.fixture
def mock_account():
    account = Mock()
    account.TradeAllowed.return_value = True
    account.TradeExpert.return_value = True
    account.Balance.return_value = 10000.0
    account.MarginLevel.return_value = 500.0
    return account

@pytest.fixture
def mock_symbol_info():
    info = Mock()
    info.TradeModeDescription.return_value = "Full Access"
    info.Name.return_value = "EURUSD"
    info.LotsMin.return_value = 0.01
    info.LotsMax.return_value = 100.0
    info.LotsStep.return_value = 0.01
    return info

@pytest.fixture
def safety_checker(mock_client, mock_account, mock_symbol_info):
    return SafetyChecker(
        client=mock_client,
        account=mock_account,
        symbol_info=mock_symbol_info,
        min_balance=1000.0,
        min_margin_level=100.0
    )

def test_check_all_pass(safety_checker):
    passed, reason = safety_checker.check_all(
        volume=0.1,
        position_count=5,
        daily_trades=10,
        max_positions=20,
        max_daily_trades=50
    )
    assert passed is True
    assert reason == "All safety checks passed"

def test_check_connection_fail(safety_checker, mock_client):
    mock_client.is_connected.return_value = False
    passed, reason = safety_checker.check_connection()
    assert passed is False
    assert "connection lost" in reason

def test_check_account_balance_fail(safety_checker, mock_account):
    mock_account.Balance.return_value = 500.0  # Below min 1000
    passed, reason = safety_checker.check_account()
    assert passed is False
    assert "Balance too low" in reason

def test_check_account_margin_fail(safety_checker, mock_account):
    mock_account.MarginLevel.return_value = 50.0  # Below min 100
    passed, reason = safety_checker.check_account()
    assert passed is False
    assert "Margin level too low" in reason

def test_check_account_trade_not_allowed(safety_checker, mock_account):
    mock_account.TradeAllowed.return_value = False
    passed, reason = safety_checker.check_account()
    assert passed is False
    assert "Trading not allowed" in reason

def test_check_symbol_disabled(safety_checker, mock_symbol_info):
    mock_symbol_info.TradeModeDescription.return_value = "Disabled"
    passed, reason = safety_checker.check_symbol()
    assert passed is False
    assert "Trading disabled" in reason

def test_check_volume_limits(safety_checker):
    # Too small
    passed, reason = safety_checker.check_volume(0.001)
    assert passed is False
    assert "below minimum" in reason
    
    # Too large
    passed, reason = safety_checker.check_volume(200.0)
    assert passed is False
    assert "above maximum" in reason
    
    # Bad step
    passed, reason = safety_checker.check_volume(0.105) # Step is 0.01
    assert passed is False
    assert "not aligned with step" in reason
    
    # Good
    passed, reason = safety_checker.check_volume(0.12)
    assert passed is True

def test_check_limits(safety_checker):
    # Position limit
    passed, reason = safety_checker.check_limits(20, 10, 20, 50)
    assert passed is False
    assert "Position limit reached" in reason
    
    # Daily trade limit
    passed, reason = safety_checker.check_limits(10, 50, 20, 50)
    assert passed is False
    assert "Daily trade limit reached" in reason
    
    # OK
    passed, reason = safety_checker.check_limits(19, 49, 20, 50)
    assert passed is True


import pytest
from unittest.mock import MagicMock, patch
from apps.mt5.account_info import AccountInfo

@pytest.fixture
def mock_api():
    api = MagicMock()
    # Setup default mock values
    api.account_info.return_value = MagicMock(_asdict=lambda: {
        "login": 123456,
        "balance": 1000.0,
        "equity": 1000.0,
        "margin": 100.0,
        "margin_free": 900.0,
        "margin_level": 1000.0
    })
    api.account_info_integer.return_value = 123456
    api.account_info_double.return_value = 1000.0
    api.account_info_string.return_value = "TestServer"
    return api

@pytest.fixture
def account_info(mock_api):
    return AccountInfo(api=mock_api)

def test_initialization(account_info, mock_api):
    assert account_info._api == mock_api

def test_fetch_account_info(account_info, mock_api):
    assert account_info._fetch_account_info() is True
    assert account_info._account_info["login"] == 123456
    
    # Test failure
    mock_api.account_info.return_value = None
    assert account_info._fetch_account_info() is False
    assert account_info._account_info == {}

def test_account_properties(account_info, mock_api):
    # Mock specific calls if needed, otherwise rely on default mock
    mock_api.account_info_integer.return_value = 123456
    assert account_info.Login() == 123456
    
    mock_api.account_info_string.return_value = "TestServer"
    assert account_info.Server() == "TestServer"
    
    mock_api.account_info_double.return_value = 1000.0
    assert account_info.Balance() == 1000.0

def test_margin_calculations(account_info, mock_api):
    mock_api.account_info_double.return_value = 900.0
    assert account_info.FreeMargin() == 900.0

def test_trading_checks(account_info, mock_api):
    mock_api.order_calc_profit.return_value = 10.0
    assert account_info.OrderProfitCheck("EURUSD", 0, 1.0, 1.1, 1.2) == 10.0
    
    mock_api.order_calc_margin.return_value = 50.0
    assert account_info.MarginCheck("EURUSD", 0, 1.0, 1.1) == 50.0


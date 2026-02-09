
from unittest.mock import Mock, patch
import pytest
from apps.live.notification_adapter import LiveTradingNotifier

@pytest.fixture
def mock_manager_cls():
    with patch("apps.live.notification_adapter.NotificationManager") as mock:
        yield mock

@pytest.fixture
def notifier(mock_manager_cls):
    return LiveTradingNotifier(
        enabled=True,
        smtp_host="host",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pwd",
        recipients=["test@example.com"]
    )

def test_init_disabled(mock_manager_cls):
    notifier = LiveTradingNotifier(
        enabled=False,
        smtp_host="host",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pwd",
        recipients=[]
    )
    assert notifier.enabled is False
    assert notifier.manager is None
    # Shouldn't create manager if disabled
    mock_manager_cls.assert_not_called()

def test_init_enabled(notifier, mock_manager_cls):
    assert notifier.enabled is True
    assert notifier.manager is not None
    mock_manager_cls.assert_called_once()

def test_notify_startup(notifier):
    notifier.notify_startup("EURUSD", "H1", 0.1)
    notifier.manager.send_system_alert.assert_called_once()
    args = notifier.manager.send_system_alert.call_args[1]
    assert "Started" in args["message"]
    assert "EURUSD" in args["details"]

def test_notify_signal_executed(notifier):
    signal = {
        "signal": "buy",
        "entry_price": 1.1000,
        "symbol": "EURUSD",
        "reason": "MACD Crossover",
        "strategy_name": "TrendFollow"
    }
    notifier.notify_signal(signal, executed=True)
    notifier.manager.send_trading_alert.assert_called_once()
    args = notifier.manager.send_trading_alert.call_args[1]
    assert args["action"] == "BUY"
    assert args["symbol"] == "EURUSD"

def test_notify_signal_failed(notifier):
    signal = {
        "signal": "sell",
        "symbol": "GBPUSD",
        "strategy_name": "Breakout"
    }
    notifier.notify_signal(signal, executed=False, error="Slippage")
    notifier.manager.send_error_alert.assert_called_once()
    args = notifier.manager.send_error_alert.call_args[1]
    assert "Execution Failed" in args["error_type"]
    assert "Slippage" in args["stack_trace"]

def test_notify_daily_summary(notifier):
    notifier.notify_daily_summary(10, 150.0, 2)
    notifier.manager.send_custom_message.assert_called_once()
    args = notifier.manager.send_custom_message.call_args[1]
    assert "Daily Trading Summary" in args["title"]
    assert "Trades Executed: 10" in args["body"]

def test_from_database():
    with patch("apps.live.notification_adapter.SQLiteDatabase") as mock_db_cls:
        mock_db = Mock()
        mock_db_cls.return_value = mock_db
        
        # Test with no creds
        mock_db.get_email_credentials.return_value = None
        mock_db.get_telegram_credentials.return_value = None
        
        notifier = LiveTradingNotifier.from_database(1)
        assert notifier.enabled is False
        
        # Test with email creds
        mock_db.get_email_credentials.return_value = {
            "smtp_host": "host",
            "smtp_port": 587,
            "smtp_user": "user",
            "smtp_password": "pwd",
            "recipients": ["a@b.com"]
        }
        
        notifier = LiveTradingNotifier.from_database(1)
        assert notifier.enabled is True
        assert notifier.manager is not None

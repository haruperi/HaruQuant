from unittest.mock import MagicMock, patch

import pytest
from apps.notifications.manager import (
    NotificationManager,
    NotificationManagerConfig,
    NotificationLevel,
    NotificationMessage,
)
from apps.notifications.base import NotificationResult


class TestNotificationManager:
    @pytest.fixture
    def manager(self):
        config = NotificationManagerConfig(enable_all=True)
        return NotificationManager(config)

    def test_init(self):
        manager = NotificationManager()
        assert manager.notifiers == {}
        
    @patch("apps.notifications.manager.EmailNotifier")
    def test_init_email(self, mock_email, manager):
        manager.config.email_config = MagicMock()
        manager._init_email_notifier()
        assert "email" in manager.notifiers
        
    @patch("apps.notifications.manager.TelegramNotifier")
    def test_init_telegram(self, mock_tg, manager):
        manager.config.telegram_config = MagicMock()
        manager._init_telegram_notifier()
        assert "telegram" in manager.notifiers

    @patch("apps.notifications.manager.SMSNotifier")
    def test_init_sms(self, mock_sms, manager):
        manager.config.sms_config = MagicMock()
        manager._init_sms_notifier()
        assert "sms" in manager.notifiers

    def test_send_notification_no_services(self, manager):
        msg = NotificationMessage(title="Test", body="Body")
        result = manager.send_notification(msg)
        assert result == {}

    def test_send_notification_disabled(self, manager):
        manager.config.enable_all = False
        msg = NotificationMessage(title="Test", body="Body")
        result = manager.send_notification(msg)
        assert result == {}

    def test_send_notification_success(self, manager):
        mock_notifier = MagicMock()
        mock_notifier.is_enabled.return_value = True
        mock_notifier.send_message.return_value = NotificationResult(success=True)
        
        manager.notifiers["test"] = mock_notifier
        # Use WARNING level to ensure it passes default filter
        msg = NotificationMessage(title="Test", body="Body", level=NotificationLevel.WARNING)
        
        result = manager.send_notification(msg)
        
        assert "test" in result
        assert result["test"].success is True
        assert manager.stats["total_sent"] == 1

    def test_send_notification_failure(self, manager):
        mock_notifier = MagicMock()
        mock_notifier.is_enabled.return_value = True
        mock_notifier.send_message.side_effect = Exception("Send failed")
        
        manager.notifiers["test"] = mock_notifier
        # Use WARNING level
        msg = NotificationMessage(title="Test", body="Body", level=NotificationLevel.WARNING)
        
        result = manager.send_notification(msg)
        
        assert result["test"].success is False
        assert "Send failed" in result["test"].error_message
        assert manager.stats["total_failed"] == 1

    def test_service_management(self, manager):
        mock_notifier = MagicMock()
        manager.notifiers["test"] = mock_notifier
        
        manager.disable_service("test")
        mock_notifier.disable.assert_called_once()
        
        manager.enable_service("test")
        mock_notifier.enable.assert_called_once()

    def test_send_trading_alert(self, manager):
        # Enable INFO level for trading alerts
        manager.config.default_levels.append(NotificationLevel.INFO)
        mock_notifier = MagicMock()
        mock_notifier.is_enabled.return_value = True
        manager.notifiers["test"] = mock_notifier
        
        manager.send_trading_alert(
            symbol="EURUSD",
            action="BUY",
            price=1.1,
            reason="Signal"
        )
        
        mock_notifier.send_message.assert_called_once()
        args = mock_notifier.send_message.call_args[0]
        assert "EURUSD" in args[0].title
        assert "BUY" in args[0].title

    def test_send_system_alert(self, manager):
        mock_notifier = MagicMock()
        mock_notifier.is_enabled.return_value = True
        manager.notifiers["test"] = mock_notifier
        
        manager.send_system_alert(
            level="ERROR",
            message="System down"
        )
        
        mock_notifier.send_message.assert_called_once()
        args = mock_notifier.send_message.call_args[0]
        assert args[0].level == NotificationLevel.ERROR
        assert "System down" in args[0].body

    def test_status_report(self, manager):
        mock_notifier = MagicMock()
        mock_notifier.name = "TestNotifier"
        mock_notifier.rate_limit.max_requests = 10
        mock_notifier.rate_limit.time_window = 60
        manager.notifiers["test"] = mock_notifier
        
        status = manager.get_service_status()
        assert "test" in status
        assert status["test"]["name"] == "TestNotifier"

    def test_stats(self, manager):
        manager.reset_statistics()
        stats = manager.get_statistics()
        assert stats["total_sent"] == 0
        assert stats["total_failed"] == 0

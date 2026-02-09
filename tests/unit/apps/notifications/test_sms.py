from unittest.mock import MagicMock, patch

import pytest
from apps.notifications.sms import (
    SMSConfig,
    SMSNotifier,
    NotificationError,
    NotificationLevel,
    NotificationMessage,
)


class TestSMSConfig:
    def test_init(self):
        config = SMSConfig(
            account_sid="AC123",
            auth_token="token",
            from_number="+1234567890"
        )
        assert config.account_sid == "AC123"


class TestSMSNotifier:
    @pytest.fixture
    def config(self):
        return SMSConfig(
            account_sid="AC123",
            auth_token="token",
            from_number="+1234567890",
            default_recipients=["+0987654321"]
        )

    @pytest.fixture
    def notifier(self, config):
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"friendly_name": "Test Account"}
            return SMSNotifier(config)

    def test_init_validation(self):
        config = SMSConfig(
            account_sid="",
            auth_token="",
            from_number=""
        )
        with pytest.raises(NotificationError):
            SMSNotifier(config)

    @patch("requests.post")
    def test_send_success(self, mock_post, notifier):
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "status": "queued",
            "sid": "SM123"
        }

        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)

        assert result.success is True
        assert "SM123" in result.message_id
        mock_post.assert_called_once()
        
        # Verify content
        args = mock_post.call_args[1]
        assert args["data"]["To"] == "+0987654321"
        assert "Test" in args["data"]["Body"]

    @patch("requests.post")
    def test_send_failure(self, mock_post, notifier):
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"message": "Invalid number"}

        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)

        assert result.success is False
        assert "Failed to send to all" in result.error_message

    def test_format_message(self, notifier):
        msg = NotificationMessage(
            title="Test", 
            body="First line\nSecond line", 
            level=NotificationLevel.WARNING
        )
        text = notifier._format_message(msg)
        
        assert "⚠️" in text
        assert "Test" in text
        assert "First line" in text
        assert len(text) <= 160

    def test_format_message_long(self, notifier):
        msg = NotificationMessage(
            title="Test", 
            body="A" * 200, 
            level=NotificationLevel.INFO
        )
        text = notifier._format_message(msg)
        assert len(text) <= 160
        assert "..." in text

    @patch("requests.get")
    def test_get_account_info(self, mock_get, notifier):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "active"}
        
        info = notifier.get_account_info()
        assert info["status"] == "active"

    @patch("requests.get")
    def test_get_message_history(self, mock_get, notifier):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"messages": [{"sid": "1"}]}
        
        history = notifier.get_message_history()
        assert len(history) == 1

    @patch("requests.get")
    def test_validate_phone(self, mock_get, notifier):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"valid": True}
        
        valid = notifier.validate_phone_number("+123")
        assert valid["valid"] is True

from unittest.mock import MagicMock, patch, mock_open

import pytest
from apps.notifications.telegram import (
    TelegramConfig,
    TelegramNotifier,
    NotificationError,
    NotificationLevel,
    NotificationMessage,
)


class TestTelegramConfig:
    def test_init(self):
        config = TelegramConfig(bot_token="123:abc")
        assert config.parse_mode == "HTML"
        
        config = TelegramConfig(bot_token="123:abc", parse_mode="Invalid")
        assert config.parse_mode == "HTML"


class TestTelegramNotifier:
    @pytest.fixture
    def config(self):
        return TelegramConfig(
            bot_token="123:abc",
            chat_ids=["123456789"]
        )

    @pytest.fixture
    def notifier(self, config):
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "ok": True,
                "result": {"username": "test_bot", "first_name": "Test Bot"}
            }
            return TelegramNotifier(config)

    def test_init_validation(self):
        config = TelegramConfig(bot_token="")
        with pytest.raises(NotificationError):
            TelegramNotifier(config)

    @patch("requests.post")
    def test_send_success(self, mock_post, notifier):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }

        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)

        assert result.success is True
        assert "12345" in result.message_id
        mock_post.assert_called_once()
        
        # Verify content
        args = mock_post.call_args[1]
        assert args["data"]["chat_id"] == "123456789"
        assert "Test" in args["data"]["text"]

    @patch("requests.post")
    def test_send_failure(self, mock_post, notifier):
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            "ok": False,
            "description": "Chat not found"
        }

        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)

        assert result.success is False
        assert "Failed to send to all" in result.error_message

    def test_format_message_html(self, notifier):
        msg = NotificationMessage(
            title="Test & Demo", 
            body="Key: Value\nLine 2", 
            level=NotificationLevel.INFO
        )
        text = notifier._format_message(msg)
        
        assert "<b>Test &amp; Demo</b>" in text
        assert "<b>Key:</b> Value" in text
        assert "ℹ️" in text

    def test_format_message_text(self, notifier):
        notifier.config.parse_mode = "Text"
        msg = NotificationMessage(
            title="Test", 
            body="Body", 
            level=NotificationLevel.INFO
        )
        text = notifier._format_message(msg)
        
        assert "Test" in text
        assert "Body" in text
        assert "HTML" not in text

    @patch("requests.post")
    def test_send_photo(self, mock_post, notifier):
        mock_post.return_value.json.return_value = {
            "ok": True,
            "result": {"message_id": 1}
        }
        
        with patch("builtins.open", mock_open(read_data=b"data")):
            result = notifier.send_photo("123", "photo.jpg")
            
        assert result.success is True
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_send_document(self, mock_post, notifier):
        mock_post.return_value.json.return_value = {
            "ok": True,
            "result": {"message_id": 1}
        }
        
        with patch("builtins.open", mock_open(read_data=b"data")):
            result = notifier.send_document("123", "doc.pdf")
            
        assert result.success is True
        mock_post.assert_called_once()

    @patch("requests.get")
    def test_get_updates(self, mock_get, notifier):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "result": [{"update_id": 1}]
        }
        
        updates = notifier.get_updates()
        assert len(updates) == 1

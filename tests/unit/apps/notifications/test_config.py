import json
import os
from unittest.mock import patch, mock_open, MagicMock

import pytest
from apps.notifications.config import NotificationConfig, NotificationPresets
from apps.notifications.base import NotificationLevel


class TestNotificationConfig:
    def test_defaults(self):
        config = NotificationConfig()
        assert config.email_enabled is False
        assert config.telegram_enabled is False
        assert config.sms_enabled is False
        assert config.enable_all is True
        assert "CRITICAL" in config.default_levels

    def test_from_env(self):
        env_vars = {
            "NOTIFICATION_EMAIL_ENABLED": "true",
            "NOTIFICATION_EMAIL_SMTP_SERVER": "smtp.test.com",
            "NOTIFICATION_TELEGRAM_ENABLED": "true",
            "NOTIFICATION_SMS_ENABLED": "true",
            "NOTIFICATION_ENABLE_ALL": "false"
        }
        
        with patch.dict(os.environ, env_vars):
            config = NotificationConfig.from_env()
            assert config.email_enabled is True
            assert config.email_smtp_server == "smtp.test.com"
            assert config.telegram_enabled is True
            assert config.sms_enabled is True
            assert config.enable_all is False

    @patch("apps.notifications.config.configparser.ConfigParser")
    def test_from_ini(self, mock_parser_class):
        # Setup mock parser instance
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        # Configure mock methods
        mock_parser.has_section.return_value = True
        mock_parser.getboolean.return_value = True
        
        # Configure get side effect for string values
        def get_side_effect(section, option, fallback=None):
            if section == "EMAIL" and option == "smtp_server": return "smtp.ini.com"
            if section == "TELEGRAM" and option == "token": return "123:abc"
            if section == "SMS" and option == "account_sid": return "AC123"
            return fallback or ""
            
        mock_parser.get.side_effect = get_side_effect
        
        config = NotificationConfig.from_ini("dummy.ini")
        
        # Verify parser usage
        mock_parser.read.assert_called_with("dummy.ini")
        
        # Verify config loaded
        assert config.email_enabled is True
        assert config.email_smtp_server == "smtp.ini.com"
        assert config.telegram_enabled is True
        assert config.sms_enabled is True

    def test_from_file_json(self):
        data = {
            "email_enabled": True,
            "email_smtp_server": "smtp.json.com"
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            config = NotificationConfig.from_file("config.json")
            assert config.email_enabled is True
            assert config.email_smtp_server == "smtp.json.com"

    def test_validate(self):
        config = NotificationConfig()
        config.email_enabled = True
        # Missing required email fields
        errors = config.validate()
        assert len(errors) > 0
        assert any("Email SMTP server" in e for e in errors)

        config.email_smtp_server = "smtp.test.com"
        config.email_username = "user"
        config.email_password = "pass"
        config.email_from_email = "test@test.com"
        config.email_default_recipients = ["test@test.com"]
        
        errors = config.validate()
        # Should be valid for email now
        assert not any("Email" in e for e in errors)

    def test_get_configs(self):
        config = NotificationConfig()
        assert config.get_email_config() is None
        
        config.email_enabled = True
        assert config.get_email_config() is not None

        assert config.get_telegram_config() is None
        config.telegram_enabled = True
        assert config.get_telegram_config() is not None

        assert config.get_sms_config() is None
        config.sms_enabled = True
        assert config.get_sms_config() is not None

    def test_presets(self):
        dev = NotificationPresets.development()
        assert dev.enable_all is False
        
        prod = NotificationPresets.production()
        assert prod.enable_all is True
        
        gmail = NotificationPresets.gmail_setup("user", "pass", ["r"])
        assert gmail.email_smtp_server == "smtp.gmail.com"

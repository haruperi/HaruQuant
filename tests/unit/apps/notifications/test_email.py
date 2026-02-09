import smtplib
from unittest.mock import MagicMock, patch, ANY

import pytest
from apps.notifications.email import (
    EmailConfig,
    EmailNotifier,
    EmailProviders,
    NotificationError,
    NotificationLevel,
    NotificationMessage,
)


class TestEmailConfig:
    def test_post_init(self):
        config = EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass"
        )
        assert config.from_email == "user"

        config = EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="custom@test.com"
        )
        assert config.from_email == "custom@test.com"


class TestEmailNotifier:
    @pytest.fixture
    def config(self):
        return EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="from@test.com",
            default_recipients=["to@test.com"]
        )

    @pytest.fixture
    def notifier(self, config):
        return EmailNotifier(config)

    def test_init_validation(self):
        config = EmailConfig(
            smtp_server="",
            smtp_port=0,
            username="",
            password=""
        )
        with pytest.raises(NotificationError):
            EmailNotifier(config)

    @patch("smtplib.SMTP")
    def test_send_success(self, mock_smtp, notifier):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)

        assert result.success is True
        assert result.message_id.startswith("email_")
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_failure(self, mock_smtp, notifier):
        mock_smtp.side_effect = Exception("SMTP Error")

        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)

        assert result.success is False
        assert "SMTP Error" in result.error_message

    @patch("smtplib.SMTP")
    def test_send_no_recipients(self, mock_smtp, config):
        config.default_recipients = []
        notifier = EmailNotifier(config)
        
        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send(msg)
        
        assert result.success is False
        assert "No recipients specified" in result.error_message

    @patch("smtplib.SMTP_SSL")
    def test_connection_ssl(self, mock_smtp_ssl, config):
        config.use_ssl = True
        notifier = EmailNotifier(config)
        
        with patch("ssl.create_default_context"):
            notifier._get_connection()
            mock_smtp_ssl.assert_called_with("smtp.test.com", 587, context=ANY)

    @patch("smtplib.SMTP")
    def test_connection_tls(self, mock_smtp, config):
        config.use_tls = True
        config.use_ssl = False
        notifier = EmailNotifier(config)
        
        server = notifier._get_connection()
        mock_smtp.assert_called_with("smtp.test.com", 587)
        server.starttls.assert_called_once()

    @patch("smtplib.SMTP")
    def test_test_connection_success(self, mock_smtp, notifier):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        assert notifier.test_connection() is True
        mock_server.login.assert_called_with("user", "pass")

    @patch("smtplib.SMTP")
    def test_test_connection_failure(self, mock_smtp, notifier):
        mock_smtp.side_effect = Exception("Connection failed")
        assert notifier.test_connection() is False


class TestEmailProviders:
    def test_providers(self):
        gmail = EmailProviders.gmail("user", "pass")
        assert gmail.smtp_server == "smtp.gmail.com"
        assert gmail.smtp_port == 587

        outlook = EmailProviders.outlook("user", "pass")
        assert outlook.smtp_server == "smtp-mail.outlook.com"
        
        yahoo = EmailProviders.yahoo("user", "pass")
        assert yahoo.smtp_server == "smtp.mail.yahoo.com"
        
        custom = EmailProviders.custom("smtp.custom.com", 25, "user", "pass")
        assert custom.smtp_server == "smtp.custom.com"

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from apps.notifications.base import (
    BaseNotifier,
    NotificationError,
    NotificationLevel,
    NotificationMessage,
    NotificationResult,
    NotificationTemplate,
    RateLimiter,
)


class MockNotifier(BaseNotifier):
    def __init__(self, name="mock", rate_limit=None):
        super().__init__(name, rate_limit)
        self.sent_messages = []
        self.should_fail = False
        self.fail_count = 0
        self.current_fail = 0

    def send(self, message: NotificationMessage) -> NotificationResult:
        if self.should_fail:
            return NotificationResult(success=False, error_message="Simulated failure")
            
        if self.current_fail < self.fail_count:
            self.current_fail += 1
            raise Exception("Simulated exception")
            
        self.sent_messages.append(message)
        return NotificationResult(success=True, message_id="123")

    def test_connection(self) -> bool:
        return not self.should_fail


class TestNotificationLevel:
    def test_enum_values(self):
        assert NotificationLevel.DEBUG.value == "DEBUG"
        assert NotificationLevel.INFO.value == "INFO"
        assert NotificationLevel.WARNING.value == "WARNING"
        assert NotificationLevel.ERROR.value == "ERROR"
        assert NotificationLevel.CRITICAL.value == "CRITICAL"


class TestNotificationMessage:
    def test_valid_message(self):
        msg = NotificationMessage(title="Test", body="Body")
        assert msg.title == "Test"
        assert msg.body == "Body"
        assert msg.level == NotificationLevel.INFO
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}
        assert msg.recipients == []

    def test_validation(self):
        with pytest.raises(NotificationError):
            NotificationMessage(title="", body="Body")
        with pytest.raises(NotificationError):
            NotificationMessage(title="Test", body="")

    def test_level_conversion(self):
        msg = NotificationMessage(title="Test", body="Body", level="ERROR")
        assert msg.level == NotificationLevel.ERROR


class TestRateLimiter:
    def test_allow_request(self):
        limiter = RateLimiter(max_requests=2, time_window=1)
        assert limiter.can_send() is True
        assert limiter.can_send() is True
        assert limiter.can_send() is False

    def test_window_expiry(self):
        limiter = RateLimiter(max_requests=1, time_window=0.1)
        assert limiter.can_send() is True
        assert limiter.can_send() is False
        time.sleep(0.2)
        assert limiter.can_send() is True

    def test_wait_time(self):
        limiter = RateLimiter(max_requests=1, time_window=10)
        limiter.can_send()
        wait = limiter.get_wait_time()
        assert 0 < wait <= 10


class TestBaseNotifier:
    def test_init(self):
        notifier = MockNotifier()
        assert notifier.name == "mock"
        assert notifier.enabled is True
        assert notifier.retry_attempts == 3

    def test_enable_disable(self):
        notifier = MockNotifier()
        notifier.disable()
        assert notifier.is_enabled() is False
        result = notifier.send_message(NotificationMessage(title="T", body="B"))
        assert result.success is False
        assert result.error_message == "Notifier is disabled"

        notifier.enable()
        assert notifier.is_enabled() is True

    def test_send_success(self):
        notifier = MockNotifier()
        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send_message(msg)
        assert result.success is True
        assert result.message_id == "123"
        assert len(notifier.sent_messages) == 1

    def test_send_retry_success(self):
        notifier = MockNotifier()
        notifier.fail_count = 2
        notifier.retry_delay = 0.01
        
        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send_message(msg)
        
        assert result.success is True
        assert result.retry_count == 2
        assert len(notifier.sent_messages) == 1

    def test_send_retry_fail(self):
        notifier = MockNotifier()
        notifier.fail_count = 5  # More than retry_attempts (3)
        notifier.retry_delay = 0.01
        
        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send_message(msg)
        
        assert result.success is False
        assert result.retry_count == 2  # 0, 1, 2 = 3 attempts
        assert len(notifier.sent_messages) == 0

    def test_rate_limit_check(self):
        limiter = MagicMock()
        limiter.can_send.return_value = False
        limiter.get_wait_time.return_value = 10
        
        notifier = MockNotifier(rate_limit=limiter)
        msg = NotificationMessage(title="Test", body="Body")
        result = notifier.send_message(msg)
        
        assert result.success is False
        assert "Rate limit exceeded" in result.error_message


class TestNotificationTemplate:
    def test_get_template(self):
        tmpl = NotificationTemplate()
        t = tmpl.get_template("trading_alert")
        assert "title" in t
        assert "body" in t
        
        with pytest.raises(NotificationError):
            tmpl.get_template("non_existent")

    def test_add_template(self):
        tmpl = NotificationTemplate()
        tmpl.add_template("new_tmpl", "{var}", "{var}")
        assert "new_tmpl" in tmpl.list_templates()

    def test_render(self):
        tmpl = NotificationTemplate()
        msg = tmpl.render("trading_alert", 
            symbol="BTC", action="BUY", price=100, 
            reason="Test", account="acc", strategy="strat", 
            risk_level="low"
        )
        assert "BTC" in msg.title
        assert "BUY" in msg.title
        assert "Test" in msg.body
        assert msg.template_name == "trading_alert"

    def test_render_missing_var(self):
        tmpl = NotificationTemplate()
        with pytest.raises(NotificationError):
            tmpl.render("trading_alert", symbol="BTC")  # Missing other vars

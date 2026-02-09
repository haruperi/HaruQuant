
import pytest
from datetime import datetime
from apps.logger.formatter import Formatter, Token
from apps.logger.record import LogRecord, Level

class MockRecord:
    def __init__(self, message, level_name="INFO", extra=None, time=None):
        self.message = message
        # Level(name, no, color, icon)
        self.level = Level(level_name, 20, "white", "")
        self.extra = extra or {}
        self.time = time or datetime.now()
        self.name = "test_logger"
        self.function = "test_func"
        self.line = 123
        self.exception = None

def test_token_parsing():
    fmt = "{time} - {message}"
    formatter = Formatter(fmt)
    assert len(formatter.tokens) == 3
    # Token(field, time), Token(literal,  - ), Token(field, message)
    assert formatter.tokens[0].type == "field"
    assert formatter.tokens[0].field_name == "time"
    assert formatter.tokens[2].field_name == "message"

def test_format_basic():
    fmt = "{level: <8} | {message}"
    formatter = Formatter(fmt)
    record = MockRecord("Hello World", "INFO")
    
    result = formatter.format(record)
    # "INFO     | Hello World"
    assert "INFO     | Hello World" in result

def test_format_with_extra():
    fmt = "{extra.user_id} : {message}"
    formatter = Formatter(fmt)
    record = MockRecord("User Action", extra={"user_id": 42})
    
    result = formatter.format(record)
    assert "42 : User Action" == result

def test_missing_field():
    fmt = "{missing_field} : {message}"
    formatter = Formatter(fmt)
    record = MockRecord("Test")
    
    result = formatter.format(record)
    assert "<missing:missing_field>" in result

def test_color_stripping():
    fmt = "<green>{message}</green>"
    formatter = Formatter(fmt, colorize=False) # Should strip tags if parsed? or just ignore?
    # Formatter logic: if colorize=False, _apply_colors is skipped, but tokens are still processed.
    # If Tokens are created for tags, they just don't add ANSI codes.
    record = MockRecord("Colored Message")
    result = formatter.format(record)
    assert result == "Colored Message"
    
    # If colorize=True
    formatter = Formatter(fmt, colorize=True)
    result = formatter.format(record)
    assert "\x1b" in result # ANSI code present

def test_datetime_formatting():
    fmt = "{time:YYYY-MM-DD}"
    formatter = Formatter(fmt)
    dt = datetime(2023, 1, 1, 12, 0, 0)
    record = MockRecord("Test", time=dt)
    
    result = formatter.format(record)
    assert result == "2023-01-01"

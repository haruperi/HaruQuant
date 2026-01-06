import unittest
from datetime import datetime
from apps.logger.formatter import Formatter, Token
from apps.logger.record import LogRecord, Level, FileInfo, ProcessInfo, ThreadInfo

class TestFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = Formatter(colorize=False)
        self.record = LogRecord(
            elapsed=None,
            exception=None,
            extra={"user_id": 42},
            file=FileInfo(name="test.py", path="/path/to/test.py"),
            function="test_func",
            level=Level(name="INFO", no=20, color="white", icon="I"),
            line=10,
            message="Test message",
            module="test_module",
            name="test_logger",
            process=ProcessInfo(id=123, name="Process"),
            thread=ThreadInfo(id=456, name="Thread"),
            time=datetime(2023, 1, 1, 12, 0, 0),
        )

    def test_init_defaults(self):
        f = Formatter()
        self.assertEqual(f.format_string, "{time} | {level: <8} | {name}:{function}:{line} - {message}")
        self.assertFalse(f.colorize)
        self.assertTrue(f.backtrace)
        self.assertFalse(f.diagnose)

    def test_init_custom(self):
        f = Formatter(format_string="{message}", colorize=True, backtrace=False, diagnose=True)
        self.assertEqual(f.format_string, "{message}")
        self.assertTrue(f.colorize)
        self.assertFalse(f.backtrace)
        self.assertTrue(f.diagnose)

    def test_parse_format_string(self):
        f = Formatter("{message}")
        self.assertEqual(len(f.tokens), 1)
        self.assertEqual(f.tokens[0].type, "field")
        self.assertEqual(f.tokens[0].value, "{message}")

        f = Formatter("{level} - {message}")
        self.assertEqual(len(f.tokens), 3)
        self.assertEqual(f.tokens[0].type, "field")
        self.assertEqual(f.tokens[1].type, "literal")
        self.assertEqual(f.tokens[2].type, "field")

    def test_format_basic(self):
        f = Formatter("{level} - {message}")
        result = f.format(self.record)
        self.assertEqual(result, "INFO - Test message")

    def test_format_with_spec(self):
        f = Formatter("{level: <8} - {message}")
        result = f.format(self.record)
        self.assertEqual(result, "INFO     - Test message")

    def test_format_missing_field(self):
        f = Formatter("{missing_field}")
        result = f.format(self.record)
        self.assertIn("<missing:missing_field>", result)

    def test_format_nested_field(self):
        f = Formatter("{file.name}")
        result = f.format(self.record)
        self.assertEqual(result, "test.py")

    def test_format_extra_field(self):
        f = Formatter("{extra.user_id}")
        result = f.format(self.record)
        self.assertEqual(result, "42")
    
    def test_format_extra_missing(self):
        f = Formatter("{extra.missing}")
        result = f.format(self.record)
        # The behavior depends on implementation, based on code reading:
        # if next_part in obj.extra -> return, else return "<missing>"
        self.assertEqual(result, "<missing>")

    def test_format_color(self):
        f = Formatter("<green>{message}</green>", colorize=True)
        result = f.format(self.record)
        # Should contain ANSI codes
        self.assertIn("\x1b[", result)
        self.assertIn("Test message", result)
        
        # Test level color
        f = Formatter("<level>{level}</level>", colorize=True)
        result = f.format(self.record)
        self.assertIn("\x1b[", result) # Should be white/default for INFO but definitely colored
        self.assertIn("INFO", result)

    def test_format_escaped_braces(self):
        f = Formatter("{{escaped}}")
        result = f.format(self.record)
        self.assertEqual(result, "{escaped}")

    def test_format_exception_placeholder(self):
        # We can't easily validte ExceptionFormatter output without mocking it heavily or 
        # creating a real exception. Let's create a real exception.
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            from apps.logger.record import ExceptionInfo
            exc_info = sys.exc_info()
            self.record.exception = ExceptionInfo(
                type=exc_info[0],
                value=exc_info[1],
                traceback=exc_info[2]
            )
        
        f = Formatter("{message}")
        result = f.format(self.record)
        self.assertIn("Test message", result)
        self.assertIn("Test message", result)
        self.assertIn("ValueError: test error", result)

    def test_strip_colors(self):
        text = "<green>text</green>"
        stripped = self.formatter.strip_colors(text)
        self.assertEqual(stripped, "text")

    def test_format_error(self):
        # Simulate an error during formatting by making _process_token raise
        with patch.object(self.formatter, '_process_token', side_effect=ValueError("fail")):
            result = self.formatter.format(self.record)
            self.assertIn("FORMAT ERROR: fail", result)

    def test_get_field_value_error(self):
        # Test error handling in get_field_value
        # Use a property that raises error
        class ErrorRecord:
            @property
            def bad_field(self):
                raise ValueError("access error")
        
        err_record = ErrorRecord()
        # Mock record to be passed
        result = self.formatter.get_field_value(err_record, "bad_field")
        self.assertIn("<error:bad_field>", result)

    def test_format_datetime_fallback(self):
        # Force error in _format_datetime
        with patch('apps.logger.formatter.TimeUtils.format_time', side_effect=ValueError):
            result = self.formatter._format_datetime(datetime(2023, 1, 1), "YYYY")
            self.assertEqual(result, "2023-01-01 00:00:00")

import os
import sys
from unittest.mock import MagicMock, patch
from apps.logger.formatter import Colorizer, ExceptionFormatter

class TestColorizer(unittest.TestCase):
    def setUp(self):
        self.colorizer = Colorizer()

    def test_colorize(self):
        # Test basic color
        text = self.colorizer.colorize("text", "red")
        self.assertIn("\x1b[31m", text)
        self.assertIn("text", text)
        self.assertIn("\x1b[0m", text)

        # Test compound color
        text = self.colorizer.colorize("text", "bold+red")
        self.assertIn("\x1b[1m", text)
        self.assertIn("\x1b[31m", text)

        # Test empty/no color
        self.assertEqual(self.colorizer.colorize("text", ""), "text")
        self.assertEqual(self.colorizer.colorize("", "red"), "")
        self.assertEqual(self.colorizer.colorize("text", "invalid"), "text")

    def test_colorize_level(self):
        text = self.colorizer.colorize_level("text", "INFO")
        self.assertIn("\x1b[37m", text) # white
        
        text = self.colorizer.colorize_level("text", "ERROR")
        self.assertIn("\x1b[31m", text) # red

    def test_strip_colors(self):
        text = "\x1b[31mtext\x1b[0m"
        self.assertEqual(self.colorizer.strip_colors(text), "text")

    def test_should_colorize(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(self.colorizer.should_colorize())
        
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(self.colorizer.should_colorize())

    def test_apply_color_tag(self):
        text = self.colorizer.apply_color_tag("text", "red")
        self.assertIn("\x1b[31m", text)
        
        text = self.colorizer.apply_color_tag("text", "level", "ERROR")
        self.assertIn("\x1b[31m", text)

class TestExceptionFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = ExceptionFormatter(colorize=False, backtrace=True, diagnose=True)

    def test_format_exception_none(self):
        self.assertEqual(self.formatter.format_exception(None), "")

    def test_format_exception_tuple(self):
        try:
            raise ValueError("test")
        except ValueError:
            exc_info = sys.exc_info()
            formatted = self.formatter.format_exception(exc_info)
            self.assertIn("ValueError: test", formatted)
            self.assertIn("Traceback", formatted)

    def test_format_exception_instance(self):
        try:
            raise ValueError("test")
        except ValueError as e:
            formatted = self.formatter.format_exception(e)
            self.assertIn("ValueError: test", formatted)

    def test_format_exception_with_context(self):
        # Create a more complex exception to trigger context lines
        def raise_error():
            x = 1
            y = 0
            return x / y
        
        try:
            raise_error()
        except ZeroDivisionError:
            formatted = self.formatter.format_exception(sys.exc_info())
            self.assertIn("ZeroDivisionError: division by zero", formatted)
            self.assertIn("return x / y", formatted) # Should show code context
            self.assertIn("Variables:", formatted) # Should show variables because diagnose=True
            self.assertIn("x", formatted)
            self.assertIn("y", formatted)

    def test_format_exception_no_backtrace(self):
        f = ExceptionFormatter(backtrace=False)
        try:
            raise ValueError("test")
        except ValueError as e:
            formatted = f.format_exception(e)
            self.assertIn("ValueError: test", formatted)
            self.assertNotIn("Traceback", formatted)

    def test_format_exception_only(self):
        formatted = self.formatter.format_exception_only(ValueError, ValueError("msg"))
        self.assertEqual(formatted, "ValueError: msg")

    def test_shorten_path(self):
        # Test path shortening logic
        path = "/a/very/long/path/that/needs/shortening/file.py"
        short = self.formatter._shorten_path(path)
        # Implementation detail: returns ".../needs/shortening/file.py" or similar
        self.assertTrue(short.endswith("file.py"))
        
        # Test site-packages
        # Test site-packages
        path = os.path.join("usr", "lib", "python3.8", "site-packages", "package", "module.py")
        short = self.formatter._shorten_path(path)
        # Normalize backslashes for assertion
        self.assertEqual(short.replace("\\", "/"), "site-packages/package/module.py")



if __name__ == '__main__':
    unittest.main()

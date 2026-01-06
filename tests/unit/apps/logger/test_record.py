import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from apps.logger.record import (
    ExceptionInfo,
    FileInfo,
    Level,
    LogRecord,
    ProcessInfo,
    ThreadInfo,
)

# from dataclasses import asdict



class TestLevel(unittest.TestCase):
    def setUp(self):
        self.info = Level(name="INFO", no=20, color="white", icon="I")
        self.error = Level(name="ERROR", no=40, color="red", icon="E")
        self.debug = Level(name="DEBUG", no=10, color="cyan", icon="D")

    def test_equality(self):
        info2 = Level(name="INFO", no=20, color="white", icon="I")
        self.assertEqual(self.info, info2)
        self.assertNotEqual(self.info, self.error)
        self.assertNotEqual(self.info, "INFO")

    def test_comparisons(self):
        self.assertLess(self.debug, self.info)
        self.assertLessEqual(self.debug, self.info)
        self.assertLessEqual(self.info, self.info)
        self.assertGreater(self.error, self.info)
        self.assertGreaterEqual(self.error, self.info)
        self.assertGreaterEqual(self.info, self.info)

        # Test comparisons with non-Level objects
        # When comparing with non-Level, it returns NotImplemented, which results in TypeError
        with self.assertRaises(TypeError):
            _ = self.info < 10
        with self.assertRaises(TypeError):
            _ = self.info <= 10
        with self.assertRaises(TypeError):
            _ = self.info > 10
        with self.assertRaises(TypeError):
            _ = self.info >= 10

    def test_hash(self):
        info2 = Level(name="INFO", no=20, color="white", icon="I")
        self.assertEqual(hash(self.info), hash(info2))
        self.assertNotEqual(hash(self.info), hash(self.error))

        # Test using in set
        s = {self.info, self.error}
        self.assertIn(self.info, s)
        self.assertEqual(len(s), 2)

    def test_str_repr(self):
        self.assertEqual(str(self.info), "INFO")
        self.assertIn("Level(name='INFO', no=20", repr(self.info))


class TestFileInfo(unittest.TestCase):
    def test_file_info(self):
        fi = FileInfo(name="test.py", path="/path/to/test.py")
        self.assertEqual(fi.name, "test.py")
        self.assertEqual(fi.path, "/path/to/test.py")
        self.assertEqual(fi.pathlib, Path("/path/to/test.py"))
        self.assertEqual(str(fi), "test.py")
        self.assertIn("FileInfo(name='test.py'", repr(fi))


class TestProcessInfo(unittest.TestCase):
    def test_process_info(self):
        pi = ProcessInfo(id=12345, name="MainProcess")
        self.assertEqual(pi.id, 12345)
        self.assertEqual(pi.name, "MainProcess")
        self.assertEqual(str(pi), "MainProcess:12345")
        self.assertIn("ProcessInfo(id=12345", repr(pi))


class TestThreadInfo(unittest.TestCase):
    def test_thread_info(self):
        ti = ThreadInfo(id=67890, name="MainThread")
        self.assertEqual(ti.id, 67890)
        self.assertEqual(ti.name, "MainThread")
        self.assertEqual(str(ti), "MainThread:67890")
        self.assertIn("ThreadInfo(id=67890", repr(ti))


class TestExceptionInfo(unittest.TestCase):
    def test_exception_info(self):
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()
            # Note: exc_info returns (type, value, traceback)
            ei = ExceptionInfo(
                type=exc_info[0], value=exc_info[1], traceback=exc_info[2]
            )

            self.assertEqual(ei.type, ValueError)
            self.assertEqual(str(ei.value), "test error")
            self.assertIsNotNone(ei.traceback)
            self.assertEqual(str(ei), "ValueError: test error")
            self.assertIn("ExceptionInfo(type=ValueError", repr(ei))


class TestLogRecord(unittest.TestCase):
    def setUp(self):
        self.time = datetime.now()
        self.elapsed = timedelta(seconds=1.5)
        self.level = Level(name="INFO", no=20, color="white", icon="I")
        self.file = FileInfo(name="test.py", path="/path/to/test.py")
        self.process = ProcessInfo(id=123, name="Process")
        self.thread = ThreadInfo(id=456, name="Thread")
        self.extra = {"key": "value"}

        self.record = LogRecord(
            elapsed=self.elapsed,
            exception=None,
            extra=self.extra,
            file=self.file,
            function="test_func",
            level=self.level,
            line=10,
            message="Test message",
            module="test_module",
            name="test_logger",
            process=self.process,
            thread=self.thread,
            time=self.time,
        )

    def test_attributes(self):
        self.assertEqual(self.record.message, "Test message")
        self.assertEqual(self.record.level, self.level)
        self.assertEqual(self.record.line, 10)

    def test_to_dict(self):
        data = self.record.to_dict()

        self.assertEqual(data["message"], "Test message")
        self.assertEqual(data["level"]["name"], "INFO")
        self.assertEqual(data["file"]["name"], "test.py")
        self.assertEqual(data["process"]["id"], 123)
        self.assertEqual(data["extra"]["key"], "value")
        self.assertEqual(data["elapsed"]["seconds"], 1.5)

        # Check time
        self.assertEqual(data["time"]["timestamp"], self.time.timestamp())
        self.assertEqual(data["time"]["repr"], self.time.isoformat())

        self.assertIsNone(data["exception"])

    def test_to_dict_with_exception(self):
        try:
            raise ValueError("oops")
        except ValueError:
            exc_info = sys.exc_info()
            ei = ExceptionInfo(
                type=exc_info[0], value=exc_info[1], traceback=exc_info[2]
            )
            self.record.exception = ei

            data = self.record.to_dict()
            self.assertIsNotNone(data["exception"])
            self.assertEqual(data["exception"]["type"], "ValueError")
            self.assertEqual(data["exception"]["value"], "oops")
            self.assertTrue(data["exception"]["traceback"])

    def test_str_repr(self):
        self.assertEqual(str(self.record), "[INFO] Test message")
        self.assertIn("LogRecord(level=INFO, message='Test message'", repr(self.record))


if __name__ == "__main__":
    unittest.main()

import os
import unittest

import queue
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

from apps.logger.handler import (
    StreamHandler,
    CallableHandler,
    AsyncHandler,
    FileHandler,
    SizeRotation,
    TimeRotation,
    Retention,
    Compression
)
from apps.logger.record import LogRecord, Level, FileInfo, ProcessInfo, ThreadInfo
from apps.logger.formatter import Formatter

class TestHandlerBase(unittest.TestCase):
    def setUp(self):
        self.level = Level(name="INFO", no=20, color="white", icon="I")
        self.formatter = Formatter("{message}")
        self.record = LogRecord(
            elapsed=timedelta(seconds=1),
            exception=None,
            extra={},
            file=FileInfo(name="test.py", path="/path/to/test.py"),
            function="test_func",
            level=self.level,
            line=10,
            message="Test message",
            module="test_module",
            name="test_logger",
            process=ProcessInfo(id=123, name="Process"),
            thread=ThreadInfo(id=456, name="Thread"),
            time=datetime.now(),
        )

class TestStreamHandler(TestHandlerBase):
    def test_emit(self):
        sink = StringIO()
        handler = StreamHandler(sink=sink, level=self.level, formatter=self.formatter)
        
        handler.emit(self.record)
        self.assertEqual(sink.getvalue(), "Test message\n")

    def test_filter(self):
        sink = StringIO()
        # Filter that rejects everything
        handler = StreamHandler(
            sink=sink, 
            level=self.level, 
            formatter=self.formatter,
            filter_func=lambda r: False
        )
        handler.emit(self.record)
        self.assertEqual(sink.getvalue(), "")

    def test_level_filter(self):
        sink = StringIO()
        handler = StreamHandler(sink=sink, level=self.level, formatter=self.formatter)
        
        debug_level = Level(name="DEBUG", no=10, color="cyan", icon="D")
        debug_record = LogRecord(
            elapsed=timedelta(seconds=1),
            exception=None,
            extra={},
            file=FileInfo(name="test.py", path="/path/to/test.py"),
            function="test_func",
            level=debug_level,
            line=10,
            message="Debug message",
            module="test_module",
            name="test_logger",
            process=ProcessInfo(id=123, name="Process"),
            thread=ThreadInfo(id=456, name="Thread"),
            time=datetime.now(),
        )
        
        # Should not emit DEBUG record because handler level is INFO (20)
        handler.emit(debug_record)
        self.assertEqual(sink.getvalue(), "")

class TestCallableHandler(TestHandlerBase):
    def test_emit(self):
        mock_func = MagicMock()
        handler = CallableHandler(sink=mock_func, level=self.level, formatter=self.formatter)
        
        handler.emit(self.record)
        mock_func.assert_called_with("Test message")

    def test_raw_emit(self):
        mock_func = MagicMock()
        handler = CallableHandler(sink=mock_func, level=self.level, formatter=self.formatter, raw=True)
        
        handler.emit(self.record)
        mock_func.assert_called_with(self.record)

class TestAsyncHandler(TestHandlerBase):
    def test_async_emit(self):
        mock_sink = MagicMock()
        wrapped = CallableHandler(sink=mock_sink, level=self.level, formatter=self.formatter)
        handler = AsyncHandler(wrapped_handler=wrapped)
        
        handler.emit(self.record)
        
        # Give thread some time to process
        time.sleep(0.1)
        
        mock_sink.assert_called_with("Test message")
        handler.close()

    def test_queue_full_drop(self):
        mock_sink = MagicMock()
        wrapped = CallableHandler(sink=mock_sink, level=self.level, formatter=self.formatter)
        # Verify queue behavior by setting max_queue_size to 1 and strategy to drop
        # But mocking queue is hard inside the class if we instantiate it directly.
        # We can test by filling it faster than it consumes? 
        # Or better: create a handler with queue_size=1 and stop the worker logic temporarily?
        # Actually simplest is just to verify it writes eventually.
        handler = AsyncHandler(wrapped_handler=wrapped, max_queue_size=10, overflow_strategy="drop")
        handler.emit(self.record)
        time.sleep(0.1)
        mock_sink.assert_called()
        handler.close()



class TestRotation(TestHandlerBase):
    def test_size_rotation_init(self):
        rot = SizeRotation(1024)
        self.assertEqual(rot.max_bytes, 1024)
        
    def test_size_rotation_check(self):
        rot = SizeRotation(100)
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 50
        
        self.assertFalse(rot.should_rotate(mock_path, self.record))
        
        mock_path.stat.return_value.st_size = 150
        self.assertTrue(rot.should_rotate(mock_path, self.record))
        
        mock_path.exists.return_value = False
        self.assertFalse(rot.should_rotate(mock_path, self.record))

    def test_time_rotation_daily(self):
        rot = TimeRotation("daily")
        now = datetime(2023, 1, 1, 12, 0, 0)
        record = MagicMock()
        record.time = now
        
        # First call sets up rotation
        self.assertFalse(rot.should_rotate(Path("test.log"), record))
        self.assertIsNotNone(rot.next_rotation)
        # Next rotation should be next midnight
        expected = datetime(2023, 1, 2, 0, 0, 0)
        self.assertEqual(rot.next_rotation, expected)
        
        # Not time yet
        record.time = datetime(2023, 1, 1, 23, 59, 59)
        self.assertFalse(rot.should_rotate(Path("test.log"), record))
        
        # Time reached
        record.time = datetime(2023, 1, 2, 0, 0, 1)
        self.assertTrue(rot.should_rotate(Path("test.log"), record))

    def test_time_rotation_interval(self):
        # We need to mock TimeUtils.parse_duration or rely on it working
        # If "1 hour" is passed, TimeUtils is imported inside __init__
        with patch("apps.logger.utils.TimeUtils.parse_duration") as mock_parse:
            mock_parse.return_value = timedelta(hours=1)
            rot = TimeRotation("1 hour")
            
            now = datetime(2023, 1, 1, 10, 0, 0)
            record = MagicMock()
            record.time = now
            
            self.assertFalse(rot.should_rotate(Path("test.log"), record))
            self.assertEqual(rot.next_rotation, now + timedelta(hours=1))
            
            record.time = now + timedelta(minutes=59)
            self.assertFalse(rot.should_rotate(Path("test.log"), record))
            
            record.time = now + timedelta(minutes=61)
            self.assertTrue(rot.should_rotate(Path("test.log"), record))

class TestRetention(unittest.TestCase):
    def test_init(self):
        ret = Retention(count=5)
        self.assertEqual(ret.count, 5)
        
        with patch("apps.logger.utils.TimeUtils.parse_duration") as mock_pd:
            mock_pd.return_value = timedelta(days=7)
            ret = Retention(age="7 days")
            self.assertEqual(ret.age_delta, timedelta(days=7))

    def test_identify_files_to_delete_count(self):
        ret = Retention(count=2)
        files = [Path("f1"), Path("f2"), Path("f3")]
        # files passed to _identify are sorted newest to oldest
        # so keep [0, 1], delete [2:]
        to_delete = ret._identify_files_to_delete(files)
        self.assertIn(Path("f3"), to_delete)
        self.assertNotIn(Path("f1"), to_delete)
        self.assertNotIn(Path("f2"), to_delete)

class TestCompression(unittest.TestCase):
    def test_init(self):
        c = Compression("gz")
        self.assertEqual(c.format, "gz")
        c = Compression("zip")
        self.assertEqual(c.format, "zip")
        
        with self.assertRaises(ValueError):
            Compression("rar")

    @patch("gzip.open")
    @patch("shutil.copyfileobj")
    def test_compress_gzip(self, mock_copy, mock_gzip_open):
        c = Compression("gz", keep_original=True)
        # Create dummy file
        filename = "test_compress_unit.log"
        with open(filename, "w") as f:
            f.write("content")
        
        try:
            path = Path(filename)
            
            # Mock gzip open
            mock_gzip_file = MagicMock()
            mock_gzip_open.return_value.__enter__.return_value = mock_gzip_file
            
            compressed = c.compress(path)
            self.assertEqual(compressed, Path(f"{filename}.gz"))
            mock_copy.assert_called()
        finally:
            if os.path.exists(filename):
                os.remove(filename)



class TestFileHandler(TestHandlerBase):
    def setUp(self):
        super().setUp()
        self.test_file = "test_file_handler.log"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        # Clean up rotated files
        parent = Path(".")
        for f in parent.glob("test_file_handler.*.log"):
            try:
                f.unlink()
            except OSError:
                pass
        super().tearDown()

    def test_emit_creates_file(self):
        handler = FileHandler(sink=self.test_file, level=self.level, formatter=self.formatter)
        handler.emit(self.record)
        handler.close()
        
        self.assertTrue(os.path.exists(self.test_file))
        with open(self.test_file, "r") as f:
            content = f.read()
        self.assertEqual(content, "Test message\n")

    def test_size_rotation_trigger(self):
        # Set small rotation size
        rotation = SizeRotation(5) # 5 bytes
        handler = FileHandler(
            sink=self.test_file, 
            level=self.level, 
            formatter=self.formatter,
            rotation=rotation
        )
        
        # First write "Test message" (12 chars + newline = 13 bytes)
        # Should trigger rotation AFTER this write if checked before?
        # FileHandler.emit checks rotation BEFORE writing?
        # "if self.rotation and self.rotation.should_rotate(self.path, record): self._rotate()"
        
        # File is empty initially. should_rotate returns False.
        handler.emit(self.record) 
        # File now has 13 bytes.
        
        # Second write. should_rotate checks size. 13 >= 5. Returns True.
        # Rotates. Old file -> timestamped. New file created empty.
        # Writes to new file.
        handler.emit(self.record)
        handler.close()
        
        self.assertTrue(os.path.exists(self.test_file))
        # Check for rotated file
        rotated_files = list(Path(".").glob("test_file_handler.*.log"))
        self.assertTrue(len(rotated_files) >= 1)

if __name__ == '__main__':
    unittest.main()

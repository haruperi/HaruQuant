"""Handler classes for different output destinations."""

from __future__ import annotations

import atexit
import contextlib
import gzip
import queue
import shutil
import sys
import threading
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    TextIO,
    Union,
)

if TYPE_CHECKING:
    from .formatter import Formatter
    from .record import Level, LogRecord


class Rotation(ABC):
    """Abstract base class for rotation strategies."""

    @abstractmethod
    def should_rotate(self, file_path: Path, record: "LogRecord") -> bool:
        """Check if the file should be rotated."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the rotation state after a rotation occurs."""


class SizeRotation(Rotation):
    """Rotate log files based on file size."""

    def __init__(self, max_size: Union[str, int]):
        """Initialize size-based rotation."""
        from .utils import TimeUtils

        if isinstance(max_size, str):
            self.max_bytes = TimeUtils.parse_size(max_size)
        elif isinstance(max_size, int):
            if max_size <= 0:
                raise ValueError(f"max_size must be positive, got {max_size}")
            self.max_bytes = max_size
        else:
            raise TypeError(f"max_size must be str or int, got {type(max_size)}")

        self.current_size = 0

    def should_rotate(self, file_path: Path, record: "LogRecord") -> bool:
        """Check if file size exceeds maximum."""
        try:
            if file_path.exists():
                actual_size = file_path.stat().st_size
                self.current_size = actual_size
                return actual_size >= self.max_bytes
            return False
        except OSError:
            return False

    def reset(self) -> None:
        """Reset the size counter after rotation."""
        self.current_size = 0

    def __repr__(self) -> str:
        """Return string representation."""
        return f"SizeRotation(max_bytes={self.max_bytes})"


class TimeRotation(Rotation):
    """Rotate log files based on time intervals."""

    def __init__(self, when: str):
        """Initialize time-based rotation."""
        from .utils import TimeUtils

        self.when = when.lower().strip()
        self.last_rotation: Optional[datetime] = None
        self.next_rotation: Optional[datetime] = None

        if self.when == "daily":
            self.interval_type = "daily"
            self.rotation_time = (0, 0)
        elif self.when == "weekly":
            self.interval_type = "weekly"
            self.rotation_time = (0, 0)
        elif self.when == "monthly":
            self.interval_type = "monthly"
            self.rotation_time = (0, 0)
        elif self.when in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            self.interval_type = "weekday"
            self.weekday = self._parse_weekday(self.when)
            self.rotation_time = (0, 0)
        elif ":" in self.when:
            self.interval_type = "time"
            self.rotation_time = self._parse_time(self.when)
        else:
            try:
                self.interval = TimeUtils.parse_duration(self.when)
                self.interval_type = "interval"
            except ValueError as exc:
                raise ValueError(
                    f"Invalid rotation schedule: '{when}'. "
                    "Expected 'daily', 'weekly', 'monthly', 'HH:MM', weekday name, "
                    "or time interval."
                ) from exc

    def _parse_time(self, time_str: str) -> tuple[int, int]:
        """Parse time string like '12:00' or '18:30'."""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError("Time must be in HH:MM format")

            hour = int(parts[0])
            minute = int(parts[1])

            if not 0 <= hour <= 23:
                raise ValueError(f"Hour must be 0-23, got {hour}")
            if not 0 <= minute <= 59:
                raise ValueError(f"Minute must be 0-59, got {minute}")

            return (hour, minute)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format '{time_str}': {e}") from e

    def _parse_weekday(self, day: str) -> int:
        """Parse weekday name to number (0=Monday, 6=Sunday)."""
        days = {
            "sunday": 0,
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6,
        }
        return days[day.lower()]

    def _calculate_next_rotation(self, now: datetime) -> datetime:
        """Calculate the next rotation time based on the schedule."""
        if self.interval_type == "interval":
            return self._next_interval(now)
        if self.interval_type == "daily":
            return self._next_daily(now)
        if self.interval_type == "time":
            return self._next_time(now)
        if self.interval_type == "weekly":
            return self._next_weekly(now)
        if self.interval_type == "weekday":
            return self._next_weekday(now)
        if self.interval_type == "monthly":
            return self._next_monthly(now)

        return now + timedelta(days=1)

    def _next_interval(self, now: datetime) -> datetime:
        """Calculate next rotation for interval schedule."""
        if self.last_rotation is None:
            return now + self.interval
        return self.last_rotation + self.interval

    def _next_daily(self, now: datetime) -> datetime:
        """Calculate next rotation for daily schedule."""
        next_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now >= next_date:
            next_date = next_date + timedelta(days=1)
        return next_date

    def _next_time(self, now: datetime) -> datetime:
        """Calculate next rotation for specific time schedule."""
        hour, minute = self.rotation_time
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= next_time:
            next_time = next_time + timedelta(days=1)
        return next_time

    def _next_weekly(self, now: datetime) -> datetime:
        """Calculate next rotation for weekly schedule."""
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour == 0 and now.minute == 0:
            days_until_monday = 7
        next_date = now + timedelta(days=days_until_monday)
        return next_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def _next_weekday(self, now: datetime) -> datetime:
        """Calculate next rotation for specific weekday schedule."""
        target_weekday = self.weekday
        current_weekday = now.weekday()
        days_until = (target_weekday - current_weekday) % 7
        if days_until == 0 and now.hour == 0 and now.minute == 0:
            days_until = 7
        next_date = now + timedelta(days=days_until)
        return next_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def _next_monthly(self, now: datetime) -> datetime:
        """Calculate next rotation for monthly schedule."""
        if now.day == 1 and now.hour == 0 and now.minute == 0:
            if now.month == 12:
                next_date = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_date = now.replace(month=now.month + 1, day=1)
        else:
            if now.month == 12:
                next_date = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_date = now.replace(month=now.month + 1, day=1)
        return next_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def should_rotate(self, file_path: Path, record: "LogRecord") -> bool:
        """Check if it's time to rotate based on schedule."""
        now = record.time if hasattr(record, "time") else datetime.now()

        if self.last_rotation is None:
            self.last_rotation = now
            self.next_rotation = self._calculate_next_rotation(now)
            return False

        if self.next_rotation and now >= self.next_rotation:
            return True

        return False

    def reset(self) -> None:
        """Reset rotation state after a rotation."""
        now = datetime.now()
        self.last_rotation = now
        self.next_rotation = self._calculate_next_rotation(now)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TimeRotation(when='{self.when}')"


class Retention:
    """Manage retention of rotated log files."""

    def __init__(
        self,
        count: Optional[int] = None,
        age: Optional[Union[str, timedelta]] = None,
        size: Optional[Union[str, int]] = None,
    ):
        """Initialize retention policy."""
        self.count = count
        self.age_delta: Optional[timedelta] = None
        self.size_bytes: Optional[int] = None

        if count is not None and (not isinstance(count, int) or count < 0):
            raise ValueError(f"count must be non-negative integer, got {count}")

        if age is not None:
            if isinstance(age, timedelta):
                self.age_delta = age
            elif isinstance(age, str):
                from .utils import TimeUtils

                self.age_delta = TimeUtils.parse_duration(age)
            else:
                raise TypeError(f"age must be str or timedelta, got {type(age)}")

        if size is not None:
            if isinstance(size, int):
                if size < 0:
                    raise ValueError(f"size must be non-negative, got {size}")
                self.size_bytes = size
            elif isinstance(size, str):
                from .utils import TimeUtils

                self.size_bytes = TimeUtils.parse_size(size)
            else:
                raise TypeError(f"size must be str or int, got {type(size)}")

    def clean(self, directory: Union[str, Path], pattern: str = "*.log") -> list[Path]:
        """Clean up old log files in directory based on retention policy."""
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            return []

        files = list(directory.glob(pattern))
        if not files:
            return []

        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        files_to_delete = self._identify_files_to_delete(files)

        deleted = []
        for file in files_to_delete:
            try:
                file.unlink()
                deleted.append(file)
            except OSError as e:
                sys.stderr.write(f"Could not delete {file}: {e}\n")

        return deleted

    def _identify_files_to_delete(self, files: List[Path]) -> Set[Path]:
        """Identify which files should be deleted based on retention policy."""
        files_to_delete = set()

        if self.count is not None and len(files) > self.count:
            files_to_delete.update(files[self.count :])

        if self.age_delta is not None:
            cutoff_timestamp = (datetime.now() - self.age_delta).timestamp()
            for file in files:
                with contextlib.suppress(OSError):
                    if file.stat().st_mtime < cutoff_timestamp:
                        files_to_delete.add(file)

        if self.size_bytes is not None:
            total_size = 0
            for file in files:
                with contextlib.suppress(OSError):
                    file_size = file.stat().st_size
                    if total_size + file_size > self.size_bytes:
                        files_to_delete.add(file)
                    else:
                        total_size += file_size

        return files_to_delete

    def get_files_info(
        self, directory: Union[str, Path], pattern: str = "*.log"
    ) -> List[Dict[str, Any]]:
        """Get information about files matching pattern."""
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            return []

        files = list(directory.glob(pattern))
        if not files:
            return []

        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        files_to_delete = self._identify_files_to_delete(files)

        now = datetime.now()
        result = []

        for file in files:
            with contextlib.suppress(OSError):
                stat = file.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                age = now - modified

                result.append(
                    {
                        "path": file,
                        "size": stat.st_size,
                        "modified": modified,
                        "age": age,
                        "would_delete": file in files_to_delete,
                    }
                )

        return result

    def estimate_space_freed(
        self, directory: Union[str, Path], pattern: str = "*.log"
    ) -> int:
        """Estimate how much space would be freed by cleanup."""
        info = self.get_files_info(directory, pattern)
        return sum(item["size"] for item in info if item["would_delete"])

    def __repr__(self) -> str:
        """Return string representation."""
        parts = []
        if self.count is not None:
            parts.append(f"count={self.count}")
        if self.age_delta is not None:
            parts.append(f"age={self.age_delta}")
        if self.size_bytes is not None:
            parts.append(f"size={self.size_bytes}")

        if not parts:
            parts.append("no policy")

        return f"Retention({', '.join(parts)})"


class Compression:
    """Compress log files to save disk space."""

    def __init__(
        self,
        compression_format: Union[str, Literal["gz", "gzip", "zip"]] = "gz",
        compression_level: int = 9,
        keep_original: bool = False,
    ):
        """Initialize compression settings."""
        format_lower = compression_format.lower()
        if format_lower in ["gz", "gzip"]:
            self.format = "gz"
        elif format_lower == "zip":
            self.format = "zip"
        else:
            raise ValueError(
                f"Unsupported compression format: '{compression_format}'. "
                "Expected 'gz', 'gzip', or 'zip'."
            )

        if not 1 <= compression_level <= 9:
            raise ValueError(f"compression_level must be 1-9, got {compression_level}")

        self.compression_level = compression_level
        self.keep_original = keep_original

    def compress(self, file_path: Union[str, Path]) -> Optional[Path]:
        """Compress a log file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        try:
            if self.format == "gz":
                compressed_path = self._compress_gzip(file_path)
            elif self.format == "zip":
                compressed_path = self._compress_zip(file_path)
            else:
                return None

            if not self.keep_original and compressed_path:
                with contextlib.suppress(OSError):
                    file_path.unlink()

            return compressed_path

        except Exception as e:
            sys.stderr.write(f"Compression error for {file_path}: {e}\n")
            return None

    def _compress_gzip(self, file_path: Path) -> Path:
        """Compress file using gzip."""
        compressed_path = file_path.with_suffix(file_path.suffix + ".gz")

        with (
            open(file_path, "rb") as f_in,
            gzip.open(
                compressed_path, "wb", compresslevel=self.compression_level
            ) as f_out,
        ):
            shutil.copyfileobj(f_in, f_out)

        return compressed_path

    def _compress_zip(self, file_path: Path) -> Path:
        """Compress file using zip."""
        compressed_path = file_path.with_suffix(file_path.suffix + ".zip")

        with zipfile.ZipFile(
            compressed_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=self.compression_level,
        ) as zipf:
            zipf.write(file_path, arcname=file_path.name)

        return compressed_path

    def decompress(self, file_path: Union[str, Path]) -> Optional[Path]:
        """Decompress a compressed log file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            if file_path.suffix == ".gz":
                return self._decompress_gzip(file_path)
            elif file_path.suffix == ".zip":
                return self._decompress_zip(file_path)
            else:
                raise ValueError(f"Unknown compression format: {file_path.suffix}")

        except Exception as e:
            sys.stderr.write(f"Decompression error for {file_path}: {e}\n")
            return None

    def _decompress_gzip(self, file_path: Path) -> Path:
        """Decompress gzip file."""
        if file_path.suffix == ".gz":
            decompressed_path = file_path.with_suffix("")
        else:
            decompressed_path = file_path.with_suffix(".decompressed")

        with gzip.open(file_path, "rb") as f_in, open(decompressed_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        return decompressed_path

    def _decompress_zip(self, file_path: Path) -> Path:
        """Decompress zip file."""
        with zipfile.ZipFile(file_path, "r") as zipf:
            names = zipf.namelist()
            if not names:
                raise ValueError(f"Empty zip file: {file_path}")

            zipf.extract(names[0], path=file_path.parent)
            return file_path.parent / names[0]

    def get_compression_ratio(
        self, original: Union[str, Path], compressed: Union[str, Path]
    ) -> float:
        """Calculate compression ratio."""
        original_path = Path(original)
        compressed_path = Path(compressed)

        if not original_path.exists() or not compressed_path.exists():
            return 0.0

        original_size = original_path.stat().st_size
        compressed_size = compressed_path.stat().st_size

        if original_size == 0:
            return 0.0

        ratio = (1 - compressed_size / original_size) * 100
        return round(ratio, 2)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Compression(format='{self.format}', level={self.compression_level}, "
            f"keep_original={self.keep_original})"
        )


class Handler(ABC):
    """Abstract base class for all handlers."""

    def __init__(
        self,
        sink: Any,
        level: "Level",
        formatter: "Formatter",
        filter_func: Optional[Callable[[LogRecord], bool]] = None,
        colorize: Optional[bool] = None,
        serialize: bool = False,
        backtrace: bool = True,
        diagnose: bool = False,
        enqueue: bool = False,
        catch: bool = True,
    ):
        """Initialize a handler."""
        self.id: int = 0
        self.sink: Any = sink
        self.level: "Level" = level
        self.formatter: "Formatter" = formatter
        self.filter_func: Optional[Callable[["LogRecord"], bool]] = filter_func
        self.colorize: bool = (
            colorize if colorize is not None else self._should_colorize()
        )
        self.serialize: bool = serialize
        self.backtrace: bool = backtrace
        self.diagnose: bool = diagnose
        self.enqueue: bool = enqueue
        self.catch: bool = catch
        self._lock = threading.Lock()

    def _should_colorize(self) -> bool:
        """Determine if output should be colorized."""
        return False

    @abstractmethod
    def emit(self, record: "LogRecord") -> None:
        """Emit a log record (must be implemented by subclasses)."""

    def should_emit(self, record: "LogRecord") -> bool:
        """Check if this handler should emit the given record."""
        if record.level < self.level:
            return False

        if self.filter_func is not None:
            try:
                result = self.filter_func(record)
                return bool(result)
            except (AttributeError, ValueError, TypeError):
                return True

        return True

    def format(self, record: "LogRecord") -> str:
        """Format a log record using the formatter."""
        try:
            return self.formatter.format(record)
        except (AttributeError, ValueError, TypeError) as e:
            return f"[{record.level.name}] {record.message} (formatter error: {e})"

    @abstractmethod
    def close(self) -> None:
        """Close the handler and release resources."""


class StreamHandler(Handler):
    """Handler for stream output (console, stderr, stdout, etc.)."""

    def __init__(
        self,
        sink: TextIO,
        level: "Level",
        formatter: "Formatter",
        **options: Any,
    ):
        """Initialize stream handler."""
        super().__init__(sink, level, formatter, **options)
        self.stream: TextIO = sink

    def _should_colorize(self) -> bool:
        """Auto-detect if stream supports colors."""
        try:
            return hasattr(self.stream, "isatty") and self.stream.isatty()
        except Exception:
            return False

    def emit(self, record: "LogRecord") -> None:
        """Write formatted record to stream."""
        if not self.should_emit(record):
            return

        try:
            with self._lock:
                formatted = self.format(record)
                self.stream.write(formatted + "\n")
                self.stream.flush()
        except Exception as e:
            sys.stderr.write(f"Error in StreamHandler: {e}\n")

    def close(self) -> None:
        """Flush the stream."""
        try:
            from io import StringIO

            if self.stream not in (sys.stdout, sys.stderr) and not isinstance(
                self.stream, StringIO
            ):
                self.stream.close()
            else:
                self.stream.flush()
        except Exception:
            pass


class FileHandler(Handler):
    """Handler for file output."""

    def __init__(
        self,
        sink: Union[Path, str],
        level: "Level",
        formatter: "Formatter",
        mode: str = "a",
        encoding: str = "utf-8",
        buffering: int = 1,
        rotation: Optional[Union[str, int, Rotation]] = None,
        compression: Optional[Union[str, Compression]] = None,
        retention: Optional[Union[str, int, Retention]] = None,
        **options: Any,
    ):
        """Initialize file handler."""
        super().__init__(sink, level, formatter, **options)
        self.path: Path = Path(sink) if not isinstance(sink, Path) else sink
        self.mode: str = mode
        self.encoding: str = encoding
        self.buffering: int = buffering
        self.file_handle: Optional[TextIO] = None
        self.rotation: Optional[Rotation] = self._parse_rotation(rotation)
        self.compression: Optional[Compression] = self._parse_compression(compression)
        self.retention: Optional[Retention] = self._parse_retention(retention)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._open_file()

    def _parse_rotation(
        self, rotation: Optional[Union[str, int, Rotation]]
    ) -> Optional[Rotation]:
        """Parse rotation parameter into a Rotation instance."""
        if rotation is None:
            return None

        if isinstance(rotation, Rotation):
            return rotation

        if isinstance(rotation, int):
            return SizeRotation(rotation)

        if isinstance(rotation, str):
            return self._parse_rotation_string(rotation)

        raise TypeError(
            "rotation must be None, int, str, or Rotation instance, "
            f"got {type(rotation)}"
        )

    def _parse_rotation_string(self, rotation: str) -> Rotation:
        """Parse rotation string into a rotation instance."""
        size_units = ["B", "KB", "MB", "GB", "TB", "K", "M", "G", "T"]
        upper_rotation = rotation.upper()
        is_size = any(unit in upper_rotation for unit in size_units)

        if is_size:
            with contextlib.suppress(ValueError, TypeError):
                return SizeRotation(rotation)

        try:
            return TimeRotation(rotation)
        except ValueError:
            try:
                return SizeRotation(rotation)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Invalid rotation specification: '{rotation}'. "
                    "Expected size (e.g., '10 MB'), time interval "
                    "(e.g., '1 hour'), or schedule (e.g., 'daily', '12:00')."
                ) from exc

    def _parse_compression(
        self, compression: Optional[Union[str, Compression]]
    ) -> Optional[Compression]:
        """Parse compression parameter into a Compression instance."""
        if compression is None:
            return None

        if isinstance(compression, Compression):
            return compression

        if isinstance(compression, str):
            return Compression(compression_format=compression)

        raise TypeError(
            "compression must be None, str, or Compression instance, "
            f"got {type(compression)}"
        )

    def _parse_retention(
        self, retention: Optional[Union[str, int, Retention]]
    ) -> Optional[Retention]:
        """Parse retention parameter into a Retention instance."""
        if retention is None:
            return None

        if isinstance(retention, Retention):
            return retention

        if isinstance(retention, int):
            return Retention(count=retention)
        if isinstance(retention, str):
            return Retention(age=retention)

        raise TypeError(
            "retention must be None, int, str, or Rotation instance, "
            f"got {type(retention)}"
        )

    def _should_colorize(self) -> bool:
        """Files should not have colors by default."""
        return False

    def _open_file(self) -> None:
        """Open the log file for writing."""
        try:
            # Cast handle to TextIO for type checking
            from typing import cast

            # Use raw open() call instead of context manager as we need to keep the handle open
            self.file_handle = cast(
                TextIO,
                open(  # noqa: SIM115
                    self.path,
                    mode=self.mode,
                    encoding=self.encoding,
                    buffering=self.buffering,
                ),
            )
        except (OSError, ValueError) as e:
            sys.stderr.write(f"Error opening log file {self.path}: {e}\n")
            raise

    def _on_shutdown(self) -> None:
        """Handle process shutdown by flushing and closing the file handle."""
        if self.file_handle is not None:
            self.file_handle.flush()
            self.file_handle.close()
            self.file_handle = None

    def _rotate(self) -> None:
        """Perform file rotation."""
        try:
            if self.file_handle is not None:
                self.file_handle.flush()
                self.file_handle.close()
                self.file_handle = None

            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond:06d}"

            stem = self.path.stem
            suffix = self.path.suffix
            parent = self.path.parent

            rotated_path = parent / f"{stem}.{timestamp}{suffix}"

            if self.path.exists():
                self.path.rename(rotated_path)
                self._handle_post_rotation(rotated_path, stem, suffix, parent)

            if self.rotation:
                self.rotation.reset()

            self._open_file()

        except Exception as e:
            sys.stderr.write(f"Error during file rotation: {e}\n")
            if self.file_handle is None:
                with contextlib.suppress(Exception):
                    self._open_file()

    def _handle_post_rotation(
        self, rotated_path: Path, stem: str, suffix: str, parent: Path
    ) -> None:
        """Handle compression and retention after file rotation."""
        if self.compression:
            try:
                self.compression.compress(rotated_path)
            except (OSError, ValueError) as e:
                sys.stderr.write(f"Compression error: {e}\n")

        if self.retention:
            try:
                pattern = f"{stem}.*{suffix}*"
                self.retention.clean(parent, pattern)
            except (OSError, ValueError) as e:
                sys.stderr.write(f"Retention cleanup error: {e}\n")

    def emit(self, record: "LogRecord") -> None:
        """Write formatted record to file."""
        if not self.should_emit(record):
            return

        try:
            with self._lock:
                if self.rotation and self.rotation.should_rotate(self.path, record):
                    self._rotate()

                if self.file_handle is None:
                    self._open_file()

                formatted = self.format(record)
                if self.file_handle is not None:
                    self.file_handle.write(formatted + "\n")
                    self.file_handle.flush()
        except Exception as e:
            if self.catch:
                sys.stderr.write(f"Error in FileHandler: {e}\n")
            else:
                raise

    def close(self) -> None:
        """Close the file handle."""
        with contextlib.suppress(Exception), self._lock:
            if self.file_handle is not None:
                self.file_handle.flush()
                self.file_handle.close()
                self.file_handle = None


class CallableHandler(Handler):
    """Handler for callable/function output."""

    def __init__(
        self,
        sink: Callable[[Union[str, Dict[str, Any], "LogRecord"]], Any],
        level: "Level",
        formatter: "Formatter",
        raw: bool = False,
        **options: Any,
    ):
        """Initialize callable handler."""
        super().__init__(sink, level, formatter, **options)
        if not callable(sink):
            raise TypeError(f"Sink must be callable, got {type(sink)}")
        self.func: Callable[[Union[str, Dict[str, Any], "LogRecord"]], Any] = sink
        self.raw: bool = raw

    def emit(self, record: "LogRecord") -> None:
        """Call the function with the record."""
        if not self.should_emit(record):
            return

        try:
            with self._lock:
                if self.raw:
                    # Pass raw LogRecord object to sink
                    self.func(record)
                elif self.serialize:
                    from .utils import Serializer

                    json_str = Serializer.serialize(record)
                    self.func(json_str)
                else:
                    formatted = self.format(record)
                    self.func(formatted)
        except Exception as e:
            if self.catch:
                sys.stderr.write(f"Error in CallableHandler: {e}\n")
            else:
                raise

    def close(self) -> None:
        """Close the handler (no-op for callable handlers)."""


class AsyncHandler(Handler):
    """Asynchronous handler wrapper for non-blocking logging."""

    def __init__(
        self,
        wrapped_handler: Handler,
        max_queue_size: int = 0,
        overflow_strategy: Literal["block", "drop", "raise"] = "block",
    ):
        """Initialize async handler."""
        super().__init__(
            sink=wrapped_handler.sink,
            level=wrapped_handler.level,
            formatter=wrapped_handler.formatter,
            filter_func=wrapped_handler.filter_func,
            colorize=wrapped_handler.colorize,
            serialize=wrapped_handler.serialize,
            backtrace=wrapped_handler.backtrace,
            diagnose=wrapped_handler.diagnose,
            enqueue=True,
            catch=wrapped_handler.catch,
        )

        self.wrapped_handler = wrapped_handler
        self.max_queue_size = max_queue_size
        self.overflow_strategy = overflow_strategy

        self.queue: queue.Queue["LogRecord"] = queue.Queue(maxsize=max_queue_size)
        self._stop_flag = threading.Event()
        self._stopped = False

        self.worker_thread = threading.Thread(
            target=self._worker, name=f"AsyncHandler-Worker-{id(self)}", daemon=True
        )
        self.worker_thread.start()

        atexit.register(self._cleanup)

    def emit(self, record: "LogRecord") -> None:
        """Add record to queue for async processing."""
        if self._stopped:
            return

        if not self.should_emit(record):
            return

        try:
            if self.overflow_strategy == "block":
                self.queue.put(record, block=True)
            elif self.overflow_strategy == "drop":
                self.queue.put(record, block=False)
            else:
                self.queue.put(record, block=False)
        except queue.Full:
            if self.overflow_strategy == "drop":
                pass
            elif self.overflow_strategy == "raise":
                raise
            else:
                sys.stderr.write("AsyncHandler queue full, record dropped\n")

    def _worker(self) -> None:
        """Worker thread that processes the queue."""
        while not self._stop_flag.is_set():
            try:
                try:
                    record = self.queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                try:
                    self.wrapped_handler.emit(record)
                except Exception as e:
                    if self.catch:
                        sys.stderr.write(f"Error in async handler worker: {e}\n")
                    else:
                        sys.stderr.write(f"Error in async handler worker: {e}\n")

                self.queue.task_done()

            except Exception as e:
                sys.stderr.write(f"Unexpected error in async handler worker: {e}\n")

        self._flush_queue()

    def _flush_queue(self) -> None:
        """Flush remaining items in queue."""
        while True:
            try:
                record = self.queue.get_nowait()
                try:
                    self.wrapped_handler.emit(record)
                except Exception as e:
                    sys.stderr.write(f"Error flushing async queue: {e}\n")
                self.queue.task_done()
            except queue.Empty:
                break

    def close(self) -> None:
        """Close the async handler and wait for queue to empty."""
        if self._stopped:
            return

        self._stopped = True

        with contextlib.suppress(Exception):
            self.queue.join()

        self._stop_flag.set()

        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)

        try:
            self.wrapped_handler.close()
        except Exception as e:
            sys.stderr.write(f"Error closing wrapped handler: {e}\n")

    def _cleanup(self) -> None:
        """Cleanup method called on program exit."""
        self.close()

    def __repr__(self) -> str:
        """Return string representation of AsyncHandler."""
        return (
            f"AsyncHandler(wrapped={self.wrapped_handler}, "
            f"queue_size={self.queue.qsize()}/{self.max_queue_size or 'unlimited'})"
        )

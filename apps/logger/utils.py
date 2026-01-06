"""Utility functions and classes."""

from __future__ import annotations

import json
import linecache
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from .record import LogRecord

# ANSI color codes - Foreground colors
COLORS = {
    "black": "\x1b[30m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
    "bright_black": "\x1b[90m",
    "bright_red": "\x1b[91m",
    "bright_green": "\x1b[92m",
    "bright_yellow": "\x1b[93m",
    "bright_blue": "\x1b[94m",
    "bright_magenta": "\x1b[95m",
    "bright_cyan": "\x1b[96m",
    "bright_white": "\x1b[97m",
    "reset": "\x1b[0m",
    "bold": "\x1b[1m",
    "dim": "\x1b[2m",
    "italic": "\x1b[3m",
    "underline": "\x1b[4m",
}

# ANSI background colors
BG_COLORS = {
    "bg_black": "\x1b[40m",
    "bg_red": "\x1b[41m",
    "bg_green": "\x1b[42m",
    "bg_yellow": "\x1b[43m",
    "bg_blue": "\x1b[44m",
    "bg_magenta": "\x1b[45m",
    "bg_cyan": "\x1b[46m",
    "bg_white": "\x1b[47m",
}

LEVEL_MAP = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}

LEVEL_NAMES = {v: k for k, v in LEVEL_MAP.items()}

DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

SIMPLE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)

MINIMAL_FORMAT = "{level: <8} | {message}"

DETAILED_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{process.id}</cyan>:<cyan>{thread.name}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{module}</cyan>:"
    "<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

JSON_FORMAT = "{message}"

DATETIME_FORMATS = {
    "YYYY": "%Y",
    "YY": "%y",
    "MMMM": "%B",
    "MMM": "%b",
    "MM": "%m",
    "M": "%-m",
    "DD": "%d",
    "D": "%-d",
    "HH": "%H",
    "H": "%-H",
    "hh": "%I",
    "h": "%-I",
    "mm": "%M",
    "m": "%-M",
    "ss": "%S",
    "s": "%-S",
    "SSS": "%f",
    "A": "%p",
    "ZZ": "%z",
    "Z": "%Z",
}

DEFAULT_ENCODING = "utf-8"
DEFAULT_BUFFER_SIZE = -1

ENV_NO_COLOR = "NO_COLOR"
ENV_LOG_LEVEL = "MYLOGGER_LEVEL"
ENV_LOG_FORMAT = "MYLOGGER_FORMAT"

SIZE_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
    "K": 1024,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
}

TIME_UNITS = {
    "microsecond": 1e-6,
    "microseconds": 1e-6,
    "us": 1e-6,
    "millisecond": 1e-3,
    "milliseconds": 1e-3,
    "ms": 1e-3,
    "second": 1,
    "seconds": 1,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "minute": 60,
    "minutes": 60,
    "m": 60,
    "min": 60,
    "mins": 60,
    "hour": 3600,
    "hours": 3600,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "day": 86400,
    "days": 86400,
    "d": 86400,
    "week": 604800,
    "weeks": 604800,
    "w": 604800,
}

DEFAULT_LOGGER_NAME = "mylogger"


class FrameInspector:
    """Inspect stack frames to extract caller information."""

    @staticmethod
    def get_caller_frame(depth: int = 0) -> Optional[FrameType]:
        """Get the caller's frame at specified depth."""
        try:
            # Access to protected member _getframe is used here to inspect the
            # stack frames and extract caller information for logging purposes.
            frame = sys._getframe(  # noqa: SLF001 # pylint: disable=protected-access
                depth + 1
            )
            return frame
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def extract_frame_info(frame: Optional[FrameType]) -> Dict[str, Any]:
        """Extract detailed information from a frame."""
        if frame is None:
            return {
                "filename": "<unknown>",
                "file_name": "<unknown>",
                "function": "<unknown>",
                "lineno": 0,
                "module": "<unknown>",
                "code_context": [],
                "context_line": "",
            }

        code = frame.f_code
        filename = code.co_filename
        function = code.co_name
        lineno = frame.f_lineno
        module = frame.f_globals.get("__name__", "__main__")

        file_name = os.path.basename(filename)

        code_context, context_line = FrameInspector._get_code_context(
            filename, lineno, context_size=5
        )

        return {
            "filename": filename,
            "file_name": file_name,
            "function": function,
            "lineno": lineno,
            "module": module,
            "code_context": code_context,
            "context_line": context_line,
        }

    @staticmethod
    def _get_code_context(
        filename: str, lineno: int, context_size: int = 5
    ) -> tuple[List[str], str]:
        """Get code context around a specific line."""
        try:
            current_line = linecache.getline(filename, lineno).rstrip()

            start_line = max(1, lineno - context_size)
            end_line = lineno + context_size + 1

            context_lines = []
            for line_num in range(start_line, end_line):
                line = linecache.getline(filename, line_num).rstrip()
                if line:
                    context_lines.append(line)

            return context_lines, current_line

        except OSError:
            return [], ""

    @staticmethod
    def clear_cache() -> None:
        """Clear the linecache."""
        linecache.checkcache()


class TimeUtils:
    """Time-related utility functions for parsing and formatting."""

    @staticmethod
    def parse_duration(duration: str) -> timedelta:
        """Parse duration string to timedelta."""
        if not duration or not isinstance(duration, str):
            raise ValueError(f"Invalid duration: {duration}")

        duration = duration.strip().lower()

        pattern = r"(\d+\.?\d*)\s*([a-z]+)"
        matches = re.findall(pattern, duration)

        if not matches:
            raise ValueError(f"Invalid duration format: {duration}")

        total_seconds = 0.0

        for value_str, unit in matches:
            try:
                value = float(value_str)
            except ValueError as exc:  # pragma: no cover
                raise ValueError(f"Invalid number: {value_str}") from exc

            if unit not in TIME_UNITS:
                raise ValueError(f"Unknown time unit: {unit}")

            total_seconds += value * TIME_UNITS[unit]

        return timedelta(seconds=total_seconds)

    @staticmethod
    def parse_size(size: str) -> int:
        """Parse size string to bytes."""
        if not size:
            raise ValueError("Size string cannot be empty")

        size_str = str(size).strip().upper()

        pattern = r"^(\d+\.?\d*)\s*([A-Z]*)$"
        match = re.match(pattern, size_str)

        if not match:
            raise ValueError(f"Invalid size format: {size}")

        value_str, unit = match.groups()

        try:
            value = float(value_str)
        except ValueError as exc:  # pragma: no cover
            raise ValueError(f"Invalid number: {value_str}") from exc

        if not unit:
            return int(value)

        if unit not in SIZE_UNITS:
            raise ValueError(f"Unknown size unit: {unit}")

        return int(value * SIZE_UNITS[unit])

    @staticmethod
    def format_time(dt: datetime, fmt: str) -> str:
        """Format datetime with custom tokens (Loguru-style)."""
        if not isinstance(dt, datetime):
            raise ValueError(f"Expected datetime object, got {type(dt)}")

        result = fmt

        sorted_tokens = sorted(
            DATETIME_FORMATS.items(), key=lambda x: len(x[0]), reverse=True
        )

        for token, strftime_code in sorted_tokens:
            if token in result:
                if token == "SSS":  # nosec B105
                    milliseconds = dt.microsecond // 1000
                    result = result.replace(token, "{:03d}".format(milliseconds))
                elif token in ["M", "D", "H", "m", "s", "h"]:
                    if sys.platform == "win32":
                        padded_token = token * 2
                        if padded_token in DATETIME_FORMATS:
                            formatted = dt.strftime(DATETIME_FORMATS[padded_token])
                            result = result.replace(token, formatted.lstrip("0") or "0")
                        else:  # pragma: no cover
                            result = result.replace(
                                token, dt.strftime(DATETIME_FORMATS[token])
                            )
                    else:  # pragma: no cover
                        result = result.replace(
                            token, dt.strftime(DATETIME_FORMATS[token])
                        )
                else:
                    result = result.replace(token, dt.strftime(strftime_code))

        return result


class Serializer:
    """Serialize log records to JSON."""

    @staticmethod
    def serialize(record: "LogRecord") -> str:
        """Serialize a log record to JSON string."""
        try:
            data = record.to_dict()
            return json.dumps(
                data, default=Serializer._json_default, ensure_ascii=False
            )
        except Exception as e:  # pylint: disable=broad-except
            # Fallback for when serialization fails.
            # We catch all exceptions here to ensure the logger itself doesn't crash.
            return json.dumps(
                {
                    "level": record.level.name,
                    "message": record.message,
                    "serialization_error": str(e),
                }
            )

    @staticmethod
    def to_dict(record: "LogRecord") -> Dict[str, Any]:
        """Convert log record to dictionary."""
        data = record.to_dict()

        sanitized = Serializer._sanitize_dict(data)
        if isinstance(sanitized, dict):
            return sanitized
        return {}  # pragma: no cover

    @staticmethod
    def _sanitize_dict(obj: Any) -> Any:
        """Recursively sanitize dictionary values for JSON serialization."""
        if isinstance(obj, dict):
            return {key: Serializer._sanitize_dict(value) for key, value in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [Serializer._sanitize_dict(item) for item in obj]
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        # Complex types and fallback
        try:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, timedelta):
                return obj.total_seconds()
            return str(obj)
        except Exception:  # pylint: disable=broad-except
            # Fallback for when str() or repr() fails.
            return repr(obj)

    @staticmethod
    def _json_default(obj: Any) -> Any:
        """Encode non-serializable objects for JSON."""
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, timedelta):
            return obj.total_seconds()

        if isinstance(obj, Path):
            return str(obj)

        if isinstance(obj, Exception):
            return {"type": type(obj).__name__, "message": str(obj), "repr": repr(obj)}

        try:
            return str(obj)
        except Exception:  # pylint: disable=broad-except
            # Fallback for when str() or repr() fails.
            return repr(obj)

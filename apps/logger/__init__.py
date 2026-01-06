"""
Logger - A Loguru-inspired logging library.

A production-ready logging library inspired by Loguru, built with
Python standard library only.
"""

from .__version__ import (
    __author__,
    __author_email__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
    __version_info__,
)
from .logger import (
    CRITICAL,
    DEBUG,
    DEFAULT_LEVELS,
    ERROR,
    INFO,
    SUCCESS,
    TRACE,
    WARNING,
    Logger,
    logger,
)
from .record import ExceptionInfo, FileInfo, Level, LogRecord, ProcessInfo, ThreadInfo

__all__ = [
    "__version__",
    "__version_info__",
    "__title__",
    "__description__",
    "__url__",
    "__author__",
    "__author_email__",
    "__license__",
    "__copyright__",
    "logger",
    "Logger",
    "TRACE",
    "DEBUG",
    "INFO",
    "SUCCESS",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "DEFAULT_LEVELS",
    "LogRecord",
    "Level",
    "FileInfo",
    "ProcessInfo",
    "ThreadInfo",
    "ExceptionInfo",
]

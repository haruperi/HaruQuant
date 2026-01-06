"""Filtering for log records."""

from typing import List, Protocol

from .record import LogRecord


class Filter(Protocol):
    """Filter protocol."""

    def __call__(self, record: LogRecord) -> bool:
        """Return True if record should be logged."""
        ...


class LevelFilter:
    """Filter by log level."""

    def __init__(self, min_level: int = 0, max_level: int = 100):
        """Initialize LevelFilter."""
        self.min_level = min_level
        self.max_level = max_level

    def __call__(self, record: LogRecord) -> bool:
        """Check if level is in range."""
        return self.min_level <= record.level.no <= self.max_level


class ModuleFilter:
    """Filter by module name."""

    def __init__(self, modules: List[str], exclude: bool = False):
        """Initialize ModuleFilter."""
        self.modules = modules
        self.exclude = exclude

    def __call__(self, record: LogRecord) -> bool:
        """Check if module matches."""
        matches = record.module in self.modules
        return not matches if self.exclude else matches

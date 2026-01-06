"""LogRecord and related data structures."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Optional, Type


@dataclass
class Level:
    """Log level information.

    Attributes:
        name: The name of the level (e.g., 'INFO', 'ERROR')
        no: The numeric level value (higher = more severe)
        color: ANSI color code name for display (e.g., 'green', 'red')
        icon: Unicode icon/emoji for the level
    """

    name: str
    no: int
    color: str
    icon: str

    def __eq__(self, other: Any) -> bool:
        """Check if two levels are equal based on numeric value."""
        if not isinstance(other, Level):
            return NotImplemented
        return self.no == other.no

    def __lt__(self, other: Any) -> bool:
        """Check if this level is less severe than another."""
        if not isinstance(other, Level):
            return NotImplemented
        return self.no < other.no

    def __le__(self, other: Any) -> bool:
        """Check if this level is less than or equal to another."""
        if not isinstance(other, Level):
            return NotImplemented
        return self.no <= other.no

    def __gt__(self, other: Any) -> bool:
        """Check if this level is more severe than another."""
        if not isinstance(other, Level):
            return NotImplemented
        return self.no > other.no

    def __ge__(self, other: Any) -> bool:
        """Check if this level is greater than or equal to another."""
        if not isinstance(other, Level):
            return NotImplemented
        return self.no >= other.no

    def __hash__(self) -> int:
        """Hash based on level name for use in sets/dicts."""
        return hash((self.name, self.no))

    def __repr__(self) -> str:
        """Return detailed representation of the level."""
        return (
            f"Level(name='{self.name}', no={self.no}, "
            f"color='{self.color}', icon='{self.icon}')"
        )

    def __str__(self) -> str:
        """Return the level name as string."""
        return self.name


@dataclass(frozen=True)
class FileInfo:
    """File information for the source code location.

    Attributes:
        name: Base name of the file (e.g., 'main.py')
        path: Full path to the file (e.g., '/home/user/app/main.py')
    """

    name: str
    path: str

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"FileInfo(name='{self.name}', path='{self.path}')"

    def __str__(self) -> str:
        """Return the file name."""
        return self.name

    @property
    def pathlib(self) -> Path:
        """Return path as a pathlib.Path object."""
        return Path(self.path)


@dataclass(frozen=True)
class ProcessInfo:
    """Process information for the current process.

    Attributes:
        id: Process ID (PID)
        name: Process name
    """

    id: int
    name: str

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"ProcessInfo(id={self.id}, name='{self.name}')"

    def __str__(self) -> str:
        """Return process name and ID."""
        return f"{self.name}:{self.id}"


@dataclass(frozen=True)
class ThreadInfo:
    """Thread information for the current thread.

    Attributes:
        id: Thread ID
        name: Thread name
    """

    id: int
    name: str

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"ThreadInfo(id={self.id}, name='{self.name}')"

    def __str__(self) -> str:
        """Return thread name and ID."""
        return f"{self.name}:{self.id}"


@dataclass(frozen=True)
class ExceptionInfo:
    """Exception information captured from sys.exc_info().

    Attributes:
        type: Exception class/type
        value: Exception instance
        traceback: Traceback object

    Note: This class is frozen (immutable) to represent a snapshot
    of the exception state at the time of logging.
    """

    type: Type[BaseException]
    value: BaseException
    traceback: Optional[TracebackType]

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"ExceptionInfo(type={self.type.__name__}, value={self.value!r})"

    def __str__(self) -> str:
        """Return exception type and message."""
        return f"{self.type.__name__}: {self.value}"


@dataclass
class LogRecord:
    """Complete log record with all context information.

    This class represents a single log entry with complete context about
    where, when, and why the log was created. It includes information about
    the source code location, process/thread, timing, and any additional
    contextual data.

    Attributes:
        elapsed: Time elapsed since logger initialization
        exception: Exception information if logging an exception
        extra: Additional context data (custom fields)
        file: File information where log originated
        function: Function name where log was called
        level: Log level (INFO, ERROR, etc.)
        line: Line number where log was called
        message: The formatted log message
        module: Module name where log originated
        name: Logger name (e.g., '__main__', 'myapp.module')
        process: Process information (PID, name)
        thread: Thread information (ID, name)
        time: Timestamp when log was created
    """

    elapsed: timedelta
    exception: Optional[ExceptionInfo]
    extra: Dict[str, Any]
    file: FileInfo
    function: str
    level: Level
    line: int
    message: str
    module: str
    name: str
    process: ProcessInfo
    thread: ThreadInfo
    time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary for serialization.

        This method converts the LogRecord to a dictionary format suitable
        for JSON serialization or other structured output formats.

        Returns:
            Dictionary with all record fields as key-value pairs

        Example:
            >>> record = LogRecord(...)
            >>> data = record.to_dict()
            >>> print(data['level']['name'])  # 'INFO'
            >>> print(data['message'])  # 'User logged in'
        """
        result = {
            "elapsed": {
                "seconds": self.elapsed.total_seconds(),
                "repr": str(self.elapsed),
            },
            "exception": None,
            "extra": self.extra.copy(),
            "file": {
                "name": self.file.name,
                "path": self.file.path,
            },
            "function": self.function,
            "level": {
                "name": self.level.name,
                "no": self.level.no,
                "icon": self.level.icon,
            },
            "line": self.line,
            "message": self.message,
            "module": self.module,
            "name": self.name,
            "process": {
                "id": self.process.id,
                "name": self.process.name,
            },
            "thread": {
                "id": self.thread.id,
                "name": self.thread.name,
            },
            "time": {
                "timestamp": self.time.timestamp(),
                "repr": self.time.isoformat(),
            },
        }

        # Add exception info if present
        if self.exception:
            result["exception"] = {
                "type": self.exception.type.__name__,
                "value": str(self.exception.value),
                "traceback": self.exception.traceback is not None,
            }

        return result

    def __repr__(self) -> str:
        """Return detailed representation for debugging.

        Returns:
            String representation showing key fields
        """
        return (
            f"LogRecord("
            f"level={self.level.name}, "
            f"message={self.message!r}, "
            f"time={self.time.isoformat()}, "
            f"file={self.file.name}, "
            f"function={self.function}, "
            f"line={self.line})"
        )

    def __str__(self) -> str:
        """Return simple string representation.

        Returns:
            Formatted log message with basic context
        """
        return f"[{self.level.name}] {self.message}"

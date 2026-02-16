"""Core Logger class implementation."""

import functools
import multiprocessing
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from apps.utils.redaction import redact_mapping, redact_text

from .formatter import Formatter
from .handler import AsyncHandler, CallableHandler, FileHandler, Handler, StreamHandler
from .record import ExceptionInfo, FileInfo, Level, LogRecord, ProcessInfo, ThreadInfo
from .utils import FrameInspector


class LoggerError(Exception):
    """Base exception for all logger-related errors."""


class HandlerNotFoundError(LoggerError):
    """Raised when attempting to access a handler that doesn't exist."""

    def __init__(self, handler_id: int):
        """Initialize HandlerNotFoundError."""
        self.handler_id = handler_id
        super().__init__(f"Handler with ID {handler_id} not found")


class InvalidLevelError(LoggerError):
    """Raised when an invalid log level is specified."""

    def __init__(self, level: Any) -> None:
        """Initialize InvalidLevelError."""
        self.level_val = level
        super().__init__(f"Invalid log level: {level}")


class RotationError(LoggerError):
    """Raised when file rotation fails."""


class FormatterError(LoggerError):
    """Raised when message formatting fails."""


class CompressionError(LoggerError):
    """Raised when log file compression fails."""


class RetentionError(LoggerError):
    """Raised when log retention cleanup fails."""


class FilterError(LoggerError):
    """Raised when a filter function fails."""


class SinkError(LoggerError):
    """Raised when a sink (handler destination) is invalid or unavailable."""


# Default log levels
TRACE = Level(name="TRACE", no=5, color="cyan", icon="T")
DEBUG = Level(name="DEBUG", no=10, color="cyan", icon="D")
INFO = Level(name="INFO", no=20, color="white", icon="I")
SUCCESS = Level(name="SUCCESS", no=25, color="green", icon="S")
WARNING = Level(name="WARNING", no=30, color="yellow", icon="W")
ERROR = Level(name="ERROR", no=40, color="red", icon="E")
CRITICAL = Level(name="CRITICAL", no=50, color="red", icon="C")

DEFAULT_LEVELS = {
    "TRACE": TRACE,
    "DEBUG": DEBUG,
    "INFO": INFO,
    "SUCCESS": SUCCESS,
    "WARNING": WARNING,
    "ERROR": ERROR,
    "CRITICAL": CRITICAL,
}


class ContextManager:
    """Context manager for temporary context binding."""

    def __init__(self, logger_obj: "Logger", **context: Any) -> None:
        """Initialize the context manager."""
        self._logger = logger_obj
        self._context: Dict[str, Any] = context
        self._saved_extra: Dict[str, Any] = {}

    def __enter__(self) -> "Logger":
        """Enter the context - add temporary context to logger."""
        self._saved_extra = self._logger.extra.copy()
        self._logger.extra.update(self._context)
        return self._logger

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context - restore previous logger state."""
        self._logger.extra = self._saved_extra

    def __repr__(self) -> str:
        """Return string representation."""
        context_keys = ", ".join(self._context.keys())
        return f"ContextManager(context=[{context_keys}])"


class BoundLogger:
    """A logger with bound contextual information."""

    def __init__(self, parent: "Logger", **bound_extra: Any) -> None:
        """Initialize a BoundLogger."""
        self._parent = parent
        self._bound_extra: Dict[str, Any] = bound_extra

    def bind(self, **kwargs: Any) -> "BoundLogger":
        """Create a new BoundLogger with additional context."""
        merged_extra = {**self._bound_extra, **kwargs}
        return BoundLogger(self._parent, **merged_extra)

    def _log_with_context(
        self, level: Union[str, int], message: str, *args: Any, **kwargs: Any
    ) -> None:
        """Log with bound context."""
        merged_extra = {**self._bound_extra}

        if "extra" in kwargs:
            merged_extra.update(kwargs.pop("extra"))

        kwargs["extra"] = merged_extra
        # pylint: disable=protected-access
        self._parent._log(level, message, *args, **kwargs)

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a trace message with bound context."""
        self._log_with_context("TRACE", message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message with bound context."""
        self._log_with_context("DEBUG", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message with bound context."""
        self._log_with_context("INFO", message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a success message with bound context."""
        self._log_with_context("SUCCESS", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message with bound context."""
        self._log_with_context("WARNING", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message with bound context."""
        self._log_with_context("ERROR", message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message with bound context."""
        self._log_with_context("CRITICAL", message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback and bound context."""
        if "exception" not in kwargs:
            kwargs["exception"] = True
        self._log_with_context("ERROR", message, *args, **kwargs)

    def log(
        self, level: Union[str, int], message: str, *args: Any, **kwargs: Any
    ) -> None:
        """Log a message at the specified level with bound context."""
        self._log_with_context(level, message, *args, **kwargs)

    def contextualize(self, **kwargs: Any) -> ContextManager:
        """Create a context manager for temporary context binding."""
        return ContextManager(self._parent, **kwargs)

    def __repr__(self) -> str:
        """Return string representation."""
        bound_keys = ", ".join(self._bound_extra.keys())
        return f"BoundLogger(bound=[{bound_keys}])"


class OptLogger:
    """Temporary logger wrapper with options applied."""

    def __init__(self, logger_instance: "Logger", **options: Any) -> None:
        """Initialize OptLogger."""
        self._logger = logger_instance
        self._options = options

    def _log_with_options(
        self, level: str, message: str, *args: Any, **kwargs: Any
    ) -> None:
        """Log with options applied."""
        depth = self._options.get("depth", 0)

        if "exception" in self._options:
            exc = self._options["exception"]
            if exc is True:
                exc_info = sys.exc_info()
                if exc_info[0] is not None:
                    kwargs["exception"] = exc_info[1]
            elif exc is not None and exc is not False:
                kwargs["exception"] = exc

        original_depth = 2 + depth
        # pylint: disable=protected-access
        self._logger._log(level, message, *args, _depth=original_depth, **kwargs)

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log trace with options."""
        self._log_with_options("TRACE", message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug with options."""
        self._log_with_options("DEBUG", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info with options."""
        self._log_with_options("INFO", message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log success with options."""
        self._log_with_options("SUCCESS", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning with options."""
        self._log_with_options("WARNING", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error with options."""
        self._log_with_options("ERROR", message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical with options."""
        self._log_with_options("CRITICAL", message, *args, **kwargs)

    def log(
        self, level: Union[str, int], message: str, *args: Any, **kwargs: Any
    ) -> None:
        """Log at specified level with options."""
        if isinstance(level, int):
            level_name: Optional[str] = None
            for name, lvl in self._logger.levels.items():
                if lvl.no == level:
                    level_name = name
                    break
            if level_name is None:
                level_name = "INFO"
            level = level_name
        self._log_with_options(level, message, *args, **kwargs)


class Logger:
    """Main logger class."""

    def __init__(self) -> None:
        """Initialize a new logger instance."""
        self.handlers: List[Handler] = []
        self.levels: Dict[str, Level] = DEFAULT_LEVELS.copy()
        self.extra: Dict[str, Any] = {}
        self.start_time: datetime = datetime.now()
        self._handler_id_counter: int = 0
        self._disabled: Set[str] = set()
        self._lock = threading.Lock()

    def add(self, sink: Any, **options: Any) -> int:
        """Add a handler to the logger."""
        with self._lock:
            level = options.get("level", "TRACE")
            format_string = options.get("format")
            filter_func = options.get("filter")
            colorize = options.get("colorize")
            serialize = options.get("serialize", False)
            backtrace = options.get("backtrace", True)
            diagnose = options.get("diagnose", False)
            enqueue = options.get("enqueue", False)

            if isinstance(level, (str, int)):
                level_obj = self._get_level(level)
            else:
                level_obj = level

            formatter = Formatter(
                format_string=format_string,
                colorize=colorize or False,
                backtrace=backtrace,
                diagnose=diagnose,
            )

            handler: Optional[Handler] = None

            if isinstance(sink, (str, Path)):
                mode = options.get("mode", "a")
                encoding = options.get("encoding", "utf-8")
                rotation = options.get("rotation")
                compression = options.get("compression")
                retention = options.get("retention")
                handler = FileHandler(
                    sink=Path(sink),
                    level=level_obj,
                    formatter=formatter,
                    mode=mode,
                    encoding=encoding,
                    rotation=rotation,
                    compression=compression,
                    retention=retention,
                    filter_func=filter_func,
                    colorize=colorize or False,
                    serialize=serialize,
                )

            elif hasattr(sink, "write") and hasattr(sink, "flush"):
                handler = StreamHandler(
                    sink=sink,
                    level=level_obj,
                    formatter=formatter,
                    filter_func=filter_func,
                    colorize=colorize,
                    serialize=serialize,
                )

            elif callable(sink):
                raw = options.get("raw", False)
                handler = CallableHandler(
                    sink=sink,
                    level=level_obj,
                    formatter=formatter,
                    raw=raw,
                    filter_func=filter_func,
                    colorize=colorize or False,
                    serialize=serialize,
                )

            else:
                raise ValueError(
                    f"Invalid sink type: {type(sink)}. "
                    f"Expected str, Path, file-like object, or callable."
                )

            if enqueue and handler is not None:
                max_queue_size = options.get("max_queue_size", 0)
                overflow_strategy = options.get("overflow_strategy", "block")
                handler = AsyncHandler(
                    wrapped_handler=handler,
                    max_queue_size=max_queue_size,
                    overflow_strategy=overflow_strategy,
                )

            if handler is None:
                raise ValueError("Failed to create handler")

            self._handler_id_counter += 1
            handler.id = self._handler_id_counter

            self.handlers.append(handler)

            return handler.id

    def remove(self, handler_id: Optional[int] = None) -> None:
        """Remove a handler by ID."""
        with self._lock:
            if handler_id is None:
                for handler in self.handlers:
                    try:
                        handler.close()
                    except Exception as e:  # pylint: disable=broad-except
                        print(f"Error closing handler: {e}", file=sys.stderr)
                self.handlers.clear()
                return

            for i, handler in enumerate(self.handlers):
                if handler.id == handler_id:
                    try:
                        handler.close()
                    except Exception as e:  # pylint: disable=broad-except
                        print(f"Error closing handler: {e}", file=sys.stderr)
                    self.handlers.pop(i)
                    return

            raise HandlerNotFoundError(handler_id=handler_id)

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a trace message."""
        self._log("TRACE", message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log("DEBUG", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self._log("INFO", message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a success message."""
        self._log("SUCCESS", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log("WARNING", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self._log("ERROR", message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        self._log("CRITICAL", message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        if "exception" not in kwargs:
            kwargs["exception"] = True

        self._log("ERROR", message, *args, **kwargs)

    def bind(self, **kwargs: Any) -> BoundLogger:
        """Create a bound logger with contextual information."""
        return BoundLogger(self, **kwargs)

    def contextualize(self, **kwargs: Any) -> ContextManager:
        """Create a context manager for temporary context binding."""
        return ContextManager(self, **kwargs)

    def log(
        self, level: Union[str, int], message: str, *args: Any, **kwargs: Any
    ) -> None:
        """Log a message at the specified level."""
        if isinstance(level, int):
            level_name = None
            for name, lvl in self.levels.items():
                if lvl.no == level:
                    level_name = name
                    break
            if level_name is None:
                raise InvalidLevelError(f"No level with number {level}")
            level = level_name

        self._log(level, message, *args, **kwargs)

    def _log(
        self,
        level: Union[str, int, Level],
        message: str,
        *args: Any,
        _depth: int = 2,
        **kwargs: Any,
    ) -> None:
        """Perform internal logging."""
        level_obj = self._get_level(level)

        exception_info = kwargs.pop("exception", None)
        if exception_info is True:
            exc_info = sys.exc_info()
            if exc_info[0] is not None:
                exception_info = ExceptionInfo(
                    type=exc_info[0], value=exc_info[1], traceback=exc_info[2]
                )
            else:
                exception_info = None
        elif isinstance(exception_info, tuple) and len(exception_info) == 3:
            exception_info = ExceptionInfo(
                type=exception_info[0],
                value=exception_info[1],
                traceback=exception_info[2],
            )
        elif isinstance(exception_info, BaseException):
            exception_info = ExceptionInfo(
                type=type(exception_info),
                value=exception_info,
                traceback=exception_info.__traceback__,
            )
        else:
            exception_info = None

        formatted_message = self._format_message(message, args, kwargs)
        formatted_message = redact_text(formatted_message)

        frame = FrameInspector.get_caller_frame(depth=_depth)
        frame_info = FrameInspector.extract_frame_info(frame)

        module_name = frame_info["module"]
        if module_name in self._disabled:
            return

        try:
            process_info = ProcessInfo(
                id=os.getpid(), name=multiprocessing.current_process().name
            )
        except Exception:  # pylint: disable=broad-except
            process_info = ProcessInfo(id=os.getpid(), name="MainProcess")

        thread_info = ThreadInfo(
            id=threading.get_ident(), name=threading.current_thread().name
        )

        file_info = FileInfo(name=frame_info["file_name"], path=frame_info["filename"])

        elapsed = datetime.now() - self.start_time

        record_extra = self.extra.copy()
        if "extra" in kwargs:
            record_extra.update(kwargs.pop("extra"))
        else:
            record_extra.update(kwargs)
        record_extra = redact_mapping(record_extra)

        record = LogRecord(
            elapsed=elapsed,
            exception=exception_info,
            extra=record_extra,
            file=file_info,
            function=frame_info["function"],
            level=level_obj,
            line=frame_info["lineno"],
            message=formatted_message,
            module=frame_info["module"],
            name=frame_info["module"],
            process=process_info,
            thread=thread_info,
            time=datetime.now(),
        )

        self._dispatch_record(record)

    def _get_level(self, level: Union[str, int, Level]) -> Level:
        """Get Level object from name or number."""
        if isinstance(level, Level):
            return level
        if isinstance(level, str):
            level_upper = level.upper()
            if level_upper not in self.levels:
                raise InvalidLevelError(f"Unknown level: {level}")
            return self.levels[level_upper]
        if isinstance(level, int):
            for lvl in self.levels.values():
                if lvl.no == level:
                    return lvl
            raise InvalidLevelError(f"No level with number {level}")

        raise InvalidLevelError(f"Invalid level type: {type(level)}")

    def _format_message(
        self, message: str, args: tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> str:
        """Format the log message with args and kwargs."""
        if not args and not kwargs:
            return message

        try:
            if args and kwargs:
                formatted = self._replace_placeholders(message, args)
                return formatted.format(**kwargs)

            if args:
                return self._replace_placeholders(message, args)

            if kwargs:
                return message.format(**kwargs)

            return message

        except (KeyError, IndexError, ValueError) as e:
            return f"{message} [FORMATTING ERROR: {e}]"

    def _replace_placeholders(self, message: str, args: tuple[Any, ...]) -> str:
        """Replace '{}' placeholders with positional arguments."""
        formatted = message
        arg_index = 0
        result = []
        i = 0
        while i < len(formatted):
            if (
                formatted[i] == "{"
                and i + 1 < len(formatted)
                and formatted[i + 1] == "}"
                and arg_index < len(args)
            ):
                result.append(str(args[arg_index]))
                arg_index += 1
                i += 2
                continue
            result.append(formatted[i])
            i += 1

        return "".join(result)

    def _dispatch_record(self, record: LogRecord) -> None:
        """Dispatch a log record to all handlers."""
        if not self.handlers:
            print(
                f"[{record.level.name}] {record.message} "
                f"({record.file.name}:{record.function}:{record.line})",
                file=sys.stderr,
            )
            return

        for handler in self.handlers:
            try:
                handler.emit(record)
            except Exception as e:  # pylint: disable=broad-except
                try:
                    sys.stderr.write(
                        f"Error in handler {handler.id} "
                        f"({type(handler).__name__}): {e}\n"
                    )
                except Exception as emit_exc:  # pylint: disable=broad-except
                    print(f"Error writing to stderr: {emit_exc}", file=sys.stderr)

    def catch(
        self,
        exception_type: Type[BaseException] = Exception,
        *,
        level: Union[str, int] = "ERROR",
        message: str = "An error occurred",
        reraise: bool = False,
        onerror: Optional[Callable[[BaseException], None]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Create decorator to catch exceptions in functions."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except exception_type as e:
                    if message:
                        self.log(level, message, exception=e)
                    else:
                        self.log(level, f"Exception in {func.__name__}", exception=e)

                    if onerror is not None and callable(onerror):
                        try:
                            onerror(e)
                        except Exception as cb_exc:  # pylint: disable=broad-except
                            print(
                                f"Error in onerror callback: {cb_exc}", file=sys.stderr
                            )

                    if reraise:
                        raise

                    return None

            return wrapper

        return decorator

    def opt(
        self,
        *,
        exception: Optional[Union[bool, BaseException]] = None,
        depth: int = 0,
        record: bool = False,
        lazy: bool = False,
    ) -> OptLogger:
        """Return a logger wrapper with options applied to the next log call."""
        return OptLogger(
            self, exception=exception, depth=depth, record=record, lazy=lazy
        )

    def add_level(
        self, name: str, no: int, color: str = "white", icon: str = ""
    ) -> None:
        """Add a custom log level."""
        level = Level(name=name.upper(), no=no, color=color, icon=icon)
        self.levels[name.upper()] = level

        method_name = name.lower()

        def log_method(
            logger_ref: "Logger", message: str, *args: Any, **kwargs: Any
        ) -> None:
            """Dynamically generated log method."""
            # pylint: disable=protected-access
            logger_ref._log(name.upper(), message, *args, **kwargs)

        setattr(Logger, method_name, log_method)

    def disable(self, name: str) -> None:
        """Disable logging from a specific module or logger."""
        self._disabled.add(name)

    def enable(self, name: str) -> None:
        """Enable logging from a previously disabled module or logger."""
        self._disabled.discard(name)


logger = Logger()

try:
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        colorize=True,
    )

    logger.add(
        "logs/app.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | {message}",
        rotation="daily",
        compression="gz",
        retention="30 days",
        colorize=False,
    )

    logger.add(
        "logs/errors.log",
        level="ERROR",
        rotation="100 MB",
        compression="gz",
        retention="90 days",
    )

    logger.add(
        "logs/access.log",
        level="INFO",
        rotation="500 MB",
        compression="gz",
        retention="30 days",
        filter=lambda r: r.extra.get("type") == "access",
    )

    logger.add(
        "logs/debug.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | {message}",
        rotation="20 MB",
        compression="gz",
        retention="7 days",
        colorize=False,
    )
except Exception as e:  # pylint: disable=broad-except
    try:
        print(f"Error adding default handlers: {e}", file=sys.stderr)
    except Exception as emit_exc:  # pylint: disable=broad-except
        print(f"Exception occurred while writing to stderr, {emit_exc}")

"""Structlog-backed adapter compatible with the existing app logger usage."""

from __future__ import annotations

import sys
import threading
import logging
import inspect
import importlib
import os
import time
from fnmatch import fnmatch
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    structlog: Any = importlib.import_module("structlog")
    _HAS_STRUCTLOG = True
except ModuleNotFoundError:  # pragma: no cover - env dependent
    structlog = None
    _HAS_STRUCTLOG = False

from apps.utils.redaction import redact_mapping, redact_text


_LEVELS: Dict[str, int] = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}
_CONTEXT_ID_KEYS = ("correlation_id", "run_id", "trace_id")
_LEVEL_ALIASES: Dict[str, str] = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
}

TRACE = "TRACE"
DEBUG = "DEBUG"
INFO = "INFO"
SUCCESS = "SUCCESS"
WARNING = "WARNING"
ERROR = "ERROR"
CRITICAL = "CRITICAL"
DEFAULT_LEVELS = dict(_LEVELS)


@dataclass
class _CompatLevel:
    name: str
    no: int


@dataclass
class CompatRecord:
    """Minimal LogRecord-compatible payload for callback sinks."""

    time: datetime
    level: _CompatLevel
    message: str
    name: str
    file: str
    function: str
    line: int
    correlation_id: str
    run_id: str
    trace_id: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _SinkEntry:
    sink: Any
    level_no: int
    raw: bool
    format_string: Optional[str]
    filter_func: Optional[Callable[[CompatRecord], bool]]
    colorize: bool
    close_on_remove: bool = False


class _Core:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.next_id = 1
        self.sinks: Dict[int, _SinkEntry] = {}
        self.min_level_no = _LEVELS["TRACE"]
        self.component_levels: Dict[str, int] = {}


_STRUCTLOG_CONFIGURED = False
_CONFIG_LOCK = threading.Lock()
_DEFAULT_FILE_SINKS_CONFIGURED = False


class _SizeAndTimeRotatingFileSink:
    """Simple file sink that rotates on max size or UTC day boundary."""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int,
        backup_count: int,
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max(1, int(max_bytes))
        self._backup_count = max(1, int(backup_count))
        self._lock = threading.Lock()
        self._stream = self._path.open("a", encoding="utf-8")
        self._next_day_rollover = self._next_utc_midnight_ts()

    def write(self, text: str) -> None:
        payload = str(text)
        payload_size = len(payload.encode("utf-8"))
        with self._lock:
            if self._should_rotate(payload_size):
                self._rotate()
            self._stream.write(payload)
            self._stream.flush()

    def flush(self) -> None:
        with self._lock:
            self._stream.flush()

    def close(self) -> None:
        with self._lock:
            self._stream.close()

    def _should_rotate(self, payload_size: int) -> bool:
        by_time = time.time() >= self._next_day_rollover
        by_size = (self._path.stat().st_size + payload_size) > self._max_bytes
        return by_time or by_size

    def _rotate(self) -> None:
        self._stream.close()
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated = self._path.with_name(f"{self._path.name}.{stamp}")
        suffix = 1
        while rotated.exists():
            rotated = self._path.with_name(f"{self._path.name}.{stamp}.{suffix}")
            suffix += 1
        if self._path.exists():
            self._path.rename(rotated)
        self._stream = self._path.open("a", encoding="utf-8")
        self._next_day_rollover = self._next_utc_midnight_ts()
        self._prune_old_backups()

    def _prune_old_backups(self) -> None:
        pattern = f"{self._path.name}.*"
        backups = [
            p
            for p in self._path.parent.iterdir()
            if p.is_file() and fnmatch(p.name, pattern)
        ]
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for old_file in backups[self._backup_count :]:
            try:
                old_file.unlink()
            except Exception:
                pass

    @staticmethod
    def _next_utc_midnight_ts() -> float:
        now = datetime.now(timezone.utc)
        next_midnight = (
            now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        )
        return next_midnight.timestamp()


def _configure_structlog() -> None:
    global _STRUCTLOG_CONFIGURED
    if not _HAS_STRUCTLOG:
        return
    if _STRUCTLOG_CONFIGURED:
        return
    with _CONFIG_LOCK:
        if _STRUCTLOG_CONFIGURED:
            return
        renderer = os.environ.get("HQT_LOG_RENDER", "console").strip().lower()
        final_renderer = (
            structlog.processors.JSONRenderer()
            if renderer == "json"
            else structlog.dev.ConsoleRenderer(colors=True)
        )

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", key="timestamp"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                final_renderer,
            ],
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
            cache_logger_on_first_use=True,
        )
        _STRUCTLOG_CONFIGURED = True


class StructlogAdapter:
    """Structlog logger adapter with backward-compatible helper methods."""

    def __init__(
        self,
        *,
        name: str = "haruquant",
        core: Optional[_Core] = None,
        bound_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        _configure_structlog()
        self._name = name
        self._core = core or _Core()
        self._bound_extra: Dict[str, Any] = bound_extra.copy() if bound_extra else {}
        if _HAS_STRUCTLOG:
            self._logger = structlog.get_logger(name).bind(**self._bound_extra)
        else:
            self._logger = logging.getLogger(name)

    def add(self, sink: Any, **options: Any) -> int:
        level_name = self._normalize_level_name(options.get("level", "INFO"))
        level_no = _LEVELS.get(level_name, _LEVELS["INFO"])
        raw = bool(options.get("raw", False))
        fmt = options.get("format")
        filter_func = options.get("filter")
        colorize_opt = options.get("colorize")
        close_on_remove = False

        resolved_sink = sink
        if isinstance(sink, (str, Path)):
            path = Path(sink)
            path.parent.mkdir(parents=True, exist_ok=True)
            resolved_sink = path.open("a", encoding="utf-8")
            close_on_remove = True

        auto_colorize = bool(
            hasattr(resolved_sink, "isatty")
            and callable(getattr(resolved_sink, "isatty"))
            and resolved_sink.isatty()
        )
        colorize = auto_colorize if colorize_opt is None else bool(colorize_opt)

        with self._core.lock:
            sink_id = self._core.next_id
            self._core.next_id += 1
            self._core.sinks[sink_id] = _SinkEntry(
                sink=resolved_sink,
                level_no=level_no,
                raw=raw,
                format_string=fmt,
                filter_func=filter_func,
                colorize=colorize,
                close_on_remove=close_on_remove,
            )
            return sink_id

    def set_min_level(self, level: Any) -> None:
        level_name = self._normalize_level_name(level)
        with self._core.lock:
            self._core.min_level_no = _LEVELS[level_name]

    def get_min_level(self) -> str:
        with self._core.lock:
            no = self._core.min_level_no
        return next((k for k, v in _LEVELS.items() if v == no), "INFO")

    def set_component_level(self, component: str, level: Any) -> None:
        level_name = self._normalize_level_name(level)
        with self._core.lock:
            self._core.component_levels[str(component)] = _LEVELS[level_name]

    def clear_component_level(self, component: str) -> None:
        with self._core.lock:
            self._core.component_levels.pop(str(component), None)

    def clear_all_component_levels(self) -> None:
        with self._core.lock:
            self._core.component_levels.clear()

    def remove(self, handler_id: Optional[int] = None) -> None:
        with self._core.lock:
            if handler_id is None:
                ids = list(self._core.sinks.keys())
            else:
                ids = [handler_id]

            for sink_id in ids:
                entry = self._core.sinks.pop(sink_id, None)
                if entry and entry.close_on_remove:
                    try:
                        entry.sink.close()
                    except Exception:
                        pass

    def flush(self) -> None:
        with self._core.lock:
            entries = list(self._core.sinks.values())

        for entry in entries:
            try:
                if hasattr(entry.sink, "flush"):
                    entry.sink.flush()
            except Exception:
                pass

    def bind(self, **kwargs: Any) -> "StructlogAdapter":
        merged = {**self._bound_extra, **kwargs}
        return StructlogAdapter(name=self._name, core=self._core, bound_extra=merged)

    @contextmanager
    def contextualize(self, **kwargs: Any):
        yield self.bind(**kwargs)

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("TRACE", message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("DEBUG", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("INFO", message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("SUCCESS", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("WARNING", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("ERROR", message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("CRITICAL", message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", True)
        self._emit("ERROR", message, *args, **kwargs)

    def log(self, level: Any, message: str, *args: Any, **kwargs: Any) -> None:
        if isinstance(level, int):
            level_name = next((k for k, v in _LEVELS.items() if v == level), "INFO")
        else:
            level_name = self._normalize_level_name(level)
        self._emit(level_name, message, *args, **kwargs)

    def _emit(self, level_name: str, message: str, *args: Any, **kwargs: Any) -> None:
        try:
            extra = kwargs.pop("extra", None) or {}
            exc_info = kwargs.pop("exc_info", None)
            format_kwargs = kwargs
            caller = self._caller_meta(depth=3)
    
            message_text = self._format_message(message, args, format_kwargs)
            safe_extra = redact_mapping({**self._bound_extra, **format_kwargs, **extra})
            safe_extra = self._ensure_context_ids(safe_extra)
            safe_message = redact_text(message_text)
            level_name = self._normalize_level_name(level_name)
            component = str(safe_extra.get("component") or self._name)
            if not self._should_log(component, _LEVELS[level_name]):
                return
    
            if _HAS_STRUCTLOG:
                event = {
                    "event": safe_message,
                    "logger": self._name,
                    "level": level_name.lower(),
                    "extra": safe_extra,
                    "file": caller["file"],
                    "function": caller["function"],
                    "line": caller["line"],
                    "correlation_id": safe_extra["correlation_id"],
                    "run_id": safe_extra["run_id"],
                    "trace_id": safe_extra["trace_id"],
                }
                if exc_info:
                    event["exc_info"] = True
    
                if level_name in {"ERROR", "CRITICAL"}:
                    self._logger.error(**event)
                elif level_name == "WARNING":
                    self._logger.warning(**event)
                elif level_name == "DEBUG":
                    self._logger.debug(**event)
                elif level_name == "TRACE":
                    self._logger.debug(**event)
                else:
                    self._logger.info(**event)
            else:
                if level_name in {"ERROR", "CRITICAL"}:
                    self._logger.error(safe_message, exc_info=bool(exc_info))
                elif level_name == "WARNING":
                    self._logger.warning(safe_message)
                elif level_name in {"DEBUG", "TRACE"}:
                    self._logger.debug(safe_message)
                else:
                    self._logger.info(safe_message)
    
            record = CompatRecord(
                time=datetime.now(),
                level=_CompatLevel(name=level_name, no=_LEVELS[level_name]),
                message=safe_message,
                name=self._name,
                file=caller["file"],
                function=caller["function"],
                line=caller["line"],
                correlation_id=safe_extra["correlation_id"],
                run_id=safe_extra["run_id"],
                trace_id=safe_extra["trace_id"],
                extra=safe_extra,
            )
            self._dispatch_to_sinks(record)
        except Exception:
            # Logging failures must not break execution flow.
            pass


    def _dispatch_to_sinks(self, record: CompatRecord) -> None:
        with self._core.lock:
            entries = list(self._core.sinks.values())

        for entry in entries:
            if record.level.no < entry.level_no:
                continue
            if entry.filter_func is not None:
                try:
                    if not entry.filter_func(record):
                        continue
                except Exception:
                    continue

            try:
                if callable(entry.sink):
                    if entry.raw:
                        entry.sink(record)
                    else:
                        entry.sink(self._format_record(record, entry.format_string, entry.colorize))
                elif hasattr(entry.sink, "write"):
                    entry.sink.write(
                        self._format_record(record, entry.format_string, entry.colorize) + "\n"
                    )
                    if hasattr(entry.sink, "flush"):
                        entry.sink.flush()
            except Exception:
                # Logging failures must not break execution flow.
                pass

    @staticmethod
    def _format_message(message: str, args: tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
        if not args and not kwargs:
            return str(message)
        try:
            return str(message).format(*args, **kwargs)
        except Exception:
            parts = [str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()]
            suffix = " ".join(parts)
            return f"{message} {suffix}".strip()

    @staticmethod
    def _format_record(record: CompatRecord, fmt: Optional[str], colorize: bool = False) -> str:
        template = fmt or "{time} | {level} | {message}"
        level_text = StructlogAdapter._colorize_level(record.level.name) if colorize else record.level.name
        payload = {
            "time": record.time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level_text,
            "level_plain": record.level.name,
            "message": record.message,
            "name": record.name,
            "file": record.file,
            "function": record.function,
            "line": record.line,
            "correlation_id": record.correlation_id,
            "run_id": record.run_id,
            "trace_id": record.trace_id,
            "extra": record.extra,
        }
        try:
            return template.format(**payload)
        except Exception:
            return f"{payload['time']} | {payload['level']} | {payload['message']}"

    @staticmethod
    def _colorize_level(level_name: str) -> str:
        colors = {
            "TRACE": "\033[36m",
            "DEBUG": "\033[34m",
            "INFO": "\033[32m",
            "SUCCESS": "\033[92m",
            "WARNING": "\033[33m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[91m",
        }
        reset = "\033[0m"
        color = colors.get(level_name.upper())
        if color is None:
            return level_name
        return f"{color}{level_name}{reset}"

    @staticmethod
    def _caller_meta(depth: int = 3) -> Dict[str, Any]:
        try:
            frame = inspect.currentframe()
            for _ in range(depth):
                if frame is None:
                    break
                frame = frame.f_back
            if frame is None:
                return {"file": "<unknown>", "function": "<unknown>", "line": 0}
            return {
                "file": Path(frame.f_code.co_filename).name,
                "function": frame.f_code.co_name,
                "line": int(frame.f_lineno),
            }
        except Exception:
            return {"file": "<unknown>", "function": "<unknown>", "line": 0}

    @staticmethod
    def _normalize_level_name(level: Any) -> str:
        if isinstance(level, int):
            # Check if it's one of our defined level numbers
            for name, val in _LEVELS.items():
                if val == level:
                    return name
            # Fallback for standard logging levels not in our dict
            if level <= 10: return "DEBUG"
            if level <= 20: return "INFO"
            if level <= 30: return "WARNING"
            if level <= 40: return "ERROR"
            return "CRITICAL"

        name = str(level).upper()
        name = _LEVEL_ALIASES.get(name, name)
        return name if name in _LEVELS else "INFO"


    def _should_log(self, component: str, level_no: int) -> bool:
        with self._core.lock:
            threshold = self._core.component_levels.get(component, self._core.min_level_no)
        return level_no >= threshold

    @staticmethod
    def _ensure_context_ids(extra: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(extra)
        for key in _CONTEXT_ID_KEYS:
            value = out.get(key)
            out[key] = "" if value is None else str(value)
        return out


logger = StructlogAdapter()


def _is_access_record(record: CompatRecord) -> bool:
    component = str(record.extra.get("component", "")).lower()
    has_http_fields = any(
        key in record.extra for key in ("method", "path", "status_code", "remote_addr")
    )
    return "access" in component or has_http_fields


def _configure_default_file_sinks() -> None:
    global _DEFAULT_FILE_SINKS_CONFIGURED
    if _DEFAULT_FILE_SINKS_CONFIGURED:
        return

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Default policy: rotate daily (UTC) or at 50MB, keep 30 backups.
    app_sink = _SizeAndTimeRotatingFileSink(
        log_dir / "app.log", max_bytes=50 * 1024 * 1024, backup_count=30
    )
    debug_sink = _SizeAndTimeRotatingFileSink(
        log_dir / "debug.log", max_bytes=50 * 1024 * 1024, backup_count=30
    )
    error_sink = _SizeAndTimeRotatingFileSink(
        log_dir / "errors.log", max_bytes=50 * 1024 * 1024, backup_count=30
    )
    access_sink = _SizeAndTimeRotatingFileSink(
        log_dir / "access.log", max_bytes=50 * 1024 * 1024, backup_count=30
    )

    logger.add(app_sink, level="INFO")
    logger.add(debug_sink, level="DEBUG")
    logger.add(error_sink, level="ERROR")
    logger.add(access_sink, level="INFO", filter=_is_access_record)

    _DEFAULT_FILE_SINKS_CONFIGURED = True


_configure_default_file_sinks()
Logger = StructlogAdapter

__all__ = [
    "StructlogAdapter",
    "Logger",
    "CompatRecord",
    "logger",
    "TRACE",
    "DEBUG",
    "INFO",
    "SUCCESS",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "DEFAULT_LEVELS",
]

"""Process-level crash handling with log flush and state persistence."""

from __future__ import annotations

import faulthandler
import json
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Any, Callable, Optional

from backend.common.logger import logger

StateProvider = Callable[[], dict[str, Any]]

_LOCK = threading.Lock()
_INSTALLED = False
_STATE_PROVIDER: Optional[StateProvider] = None
_STATE_PATH = Path("artifacts/logs/crash/crash_state.json")
_FAULT_PATH = Path("artifacts/logs/crash/faulthandler.log")


def install_crash_handler(
    *,
    state_provider: Optional[StateProvider] = None,
    state_path: str | Path | None = None,
    fault_path: str | Path | None = None,
) -> None:
    """Install crash handlers once per process."""
    global _INSTALLED
    global _STATE_PROVIDER
    global _STATE_PATH
    global _FAULT_PATH

    with _LOCK:
        if state_provider is not None:
            _STATE_PROVIDER = state_provider
        if state_path is not None:
            _STATE_PATH = Path(state_path)
        if fault_path is not None:
            _FAULT_PATH = Path(fault_path)

        if _INSTALLED:
            return

        _FAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        fault_file = _FAULT_PATH.open("a", encoding="utf-8")
        faulthandler.enable(file=fault_file, all_threads=True)

        previous_hook = sys.excepthook

        def _excepthook(exc_type, exc, tb):  # type: ignore[no-untyped-def]
            _handle_crash("uncaught_exception", exc=exc)
            previous_hook(exc_type, exc, tb)

        sys.excepthook = _excepthook

        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGABRT):
            try:
                signal.signal(sig, _signal_handler)
            except Exception:
                # Not all runtimes allow overriding all signals.
                pass

        _INSTALLED = True


def _signal_handler(signum: int, frame: FrameType | None) -> None:  # pragma: no cover
    _ = frame
    _handle_crash("signal", signal_number=signum)

    if signum in (signal.SIGINT, signal.SIGTERM):
        raise SystemExit(128 + int(signum))
    if signum == signal.SIGABRT:
        raise SystemExit(134)


def _handle_crash(kind: str, *, exc: BaseException | None = None, signal_number: int | None = None) -> None:
    payload = _build_payload(kind, exc=exc, signal_number=signal_number)
    try:
        logger.critical("Crash handler triggered", extra={"component": "crash_handler", **payload})
    except Exception:
        pass

    _flush_logs_best_effort()
    _persist_state(payload)


def _build_payload(
    kind: str,
    *,
    exc: BaseException | None,
    signal_number: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": kind,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "signal_number": signal_number,
    }
    if exc is not None:
        payload["exception_type"] = exc.__class__.__name__
        payload["exception_message"] = str(exc)

    if _STATE_PROVIDER is not None:
        try:
            payload["state"] = _STATE_PROVIDER()
        except Exception as state_exc:
            payload["state_error"] = str(state_exc)
    return payload


def _flush_logs_best_effort() -> None:
    try:
        logger.flush()
    except Exception:
        pass

    try:
        import haruquant

        if hasattr(haruquant, "flush_logs"):
            haruquant.flush_logs()
    except Exception:
        pass


def _persist_state(payload: dict[str, Any]) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _STATE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str))
            handle.write("\n")
    except Exception:
        pass


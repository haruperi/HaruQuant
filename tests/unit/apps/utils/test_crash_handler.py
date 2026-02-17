from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

from apps.utils import crash_handler as ch


class _FakeLogger:
    def __init__(self) -> None:
        self.flushed = 0
        self.critical_calls = 0

    def critical(self, *_args, **_kwargs) -> None:
        self.critical_calls += 1

    def flush(self) -> None:
        self.flushed += 1


def test_handle_crash_persists_state_and_flushes(monkeypatch) -> None:
    fake_logger = _FakeLogger()
    root = Path(".tmp_crash_handler_test")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    state_file = root / "crash_state.jsonl"

    monkeypatch.setattr(ch, "logger", fake_logger)
    monkeypatch.setattr(ch, "_STATE_PROVIDER", lambda: {"run_id": "R1", "phase": "test"})
    monkeypatch.setattr(ch, "_STATE_PATH", state_file)
    monkeypatch.setitem(sys.modules, "hqt_engine", SimpleNamespace(flush_logs=lambda: None))

    ch._handle_crash("uncaught_exception", exc=RuntimeError("boom"))

    assert fake_logger.flushed == 1
    assert fake_logger.critical_calls == 1
    lines = state_file.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    payload = json.loads(lines[-1])
    assert payload["kind"] == "uncaught_exception"
    assert payload["exception_type"] == "RuntimeError"
    assert payload["exception_message"] == "boom"
    assert payload["state"]["run_id"] == "R1"
    shutil.rmtree(root, ignore_errors=True)


def test_install_crash_handler_is_idempotent(monkeypatch) -> None:
    root = Path(".tmp_crash_handler_test_install")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ch, "_INSTALLED", False)
    monkeypatch.setattr(ch.faulthandler, "enable", lambda **_kwargs: None)
    monkeypatch.setattr(ch.signal, "signal", lambda *_args, **_kwargs: None)

    ch.install_crash_handler(
        state_path=root / "state.jsonl",
        fault_path=root / "fault.log",
    )
    ch.install_crash_handler(
        state_path=root / "state2.jsonl",
        fault_path=root / "fault2.log",
    )

    assert ch._INSTALLED is True
    shutil.rmtree(root, ignore_errors=True)

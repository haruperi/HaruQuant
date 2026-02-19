"""Logger performance/stress harness for Python + C++ bridge paths.

Run examples:
    python tests/perfomance/utils/logger_py.py
    python tests/perfomance/utils/logger_py.py --duration-seconds 60 --load-minutes 2

Toggle sections by commenting/uncommenting function calls in main().
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import apps.utils.logger as logger_mod
from apps.utils.logger import StructlogAdapter, _Core, _SizeAndTimeRotatingFileSink


@dataclass
class TestResult:
    name: str
    success: bool
    details: dict[str, Any]


def _header(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"[LOGGER PERF] {title}")
    print("=" * 72)


def _build_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Logger performance/stress harness")
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--load-minutes", type=float, default=1.0)
    parser.add_argument("--rate-per-minute", type=int, default=50_000)
    parser.add_argument("--py-threads", type=int, default=10)
    parser.add_argument("--cpp-threads", type=int, default=10)
    parser.add_argument("--rotation-size-bytes", type=int, default=256 * 1024)
    parser.add_argument("--rotation-backups", type=int, default=5)
    parser.add_argument("--quick", action="store_true", help="Use small values for smoke runs")
    return parser.parse_args()


def _safe_import_hqt_engine() -> Any | None:
    bridge_release = ROOT_DIR / "build" / "bridge" / "Release"
    vcpkg_bin = ROOT_DIR / "build" / "vcpkg_installed" / "x64-windows" / "bin"

    if bridge_release.exists():
        if str(bridge_release) not in sys.path:
            sys.path.insert(0, str(bridge_release))
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(bridge_release))

    if vcpkg_bin.exists() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(vcpkg_bin))

    try:
        import hqt_engine  # type: ignore

        return hqt_engine
    except Exception as exc:
        print(f"[LOGGER PERF] hqt_engine unavailable: {exc}")
        return None


def _make_perf_adapter(name: str = "perf_logger") -> StructlogAdapter:
    # Disable structlog stderr path for perf measurements to avoid console bottleneck noise.
    logger_mod._HAS_STRUCTLOG = False
    adapter = StructlogAdapter(name=name, core=_Core())
    if hasattr(adapter, "_logger"):
        try:
            adapter._logger.handlers = []
            adapter._logger.addHandler(logger_mod.logging.NullHandler())
            adapter._logger.propagate = False
        except Exception:
            pass
    adapter.set_min_level("TRACE")
    return adapter


def _line_integrity_stats(log_file: Path) -> dict[str, Any]:
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\|[A-Z]+\|")
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    malformed = [line for line in lines if not pattern.match(line)]
    return {
        "total_lines": len(lines),
        "malformed_lines": len(malformed),
        "first_malformed": malformed[0] if malformed else "",
    }


def _write_report(results: list[TestResult], args: argparse.Namespace) -> Path:
    out_dir = ROOT_DIR / "artifacts" / "perf" / "logger"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"logger_perf_report_{ts}.json"

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "duration_seconds": args.duration_seconds,
            "load_minutes": args.load_minutes,
            "rate_per_minute": args.rate_per_minute,
            "py_threads": args.py_threads,
            "cpp_threads": args.cpp_threads,
            "rotation_size_bytes": args.rotation_size_bytes,
            "rotation_backups": args.rotation_backups,
            "quick": args.quick,
        },
        "results": [asdict(r) for r in results],
    }
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_file


def f01_thread_safe_logging_stress_test(args: argparse.Namespace, hqt_engine: Any | None) -> TestResult:
    _header("f01_thread_safe_logging_stress_test")
    logs_dir = ROOT_DIR / "artifacts" / "perf" / "logger" / "stress"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "thread_safety_stress.log"
    if log_file.exists():
        log_file.unlink()

    adapter = _make_perf_adapter("perf_stress")
    sink = _SizeAndTimeRotatingFileSink(log_file, max_bytes=100 * 1024 * 1024, backup_count=3)
    sink_id = adapter.add(sink, level="DEBUG", format="{time}|{level_plain}|{message}")

    stop_event = threading.Event()
    lock = threading.Lock()
    py_count = 0
    cpp_emit_count = 0
    cpp_cb_count = 0
    cb_errors = 0

    def py_worker(tid: int) -> None:
        nonlocal py_count
        seq = 0
        while not stop_event.is_set():
            adapter.info(f"PY|t={tid}|n={seq}|msg=thread_stress")
            seq += 1
            with lock:
                py_count += 1

    def cpp_callback(level: str, message: str) -> None:
        nonlocal cpp_cb_count, cb_errors
        try:
            adapter.info(f"CPP|lvl={level}|{message}")
            with lock:
                cpp_cb_count += 1
        except Exception:
            with lock:
                cb_errors += 1

    cpp_threads: list[threading.Thread] = []
    if hqt_engine is not None:
        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_log_callback(cpp_callback)

        def cpp_worker(tid: int) -> None:
            nonlocal cpp_emit_count
            seq = 0
            while not stop_event.is_set():
                hqt_engine.emit_log("info", f"t={tid}|n={seq}|msg=thread_stress")
                seq += 1
                with lock:
                    cpp_emit_count += 1

        cpp_threads = [threading.Thread(target=cpp_worker, args=(i,), daemon=True) for i in range(args.cpp_threads)]
    else:
        print("[f01] hqt_engine unavailable: C++ thread portion skipped.")

    py_threads = [threading.Thread(target=py_worker, args=(i,), daemon=True) for i in range(args.py_threads)]

    start = time.perf_counter()
    for t in py_threads:
        t.start()
    for t in cpp_threads:
        t.start()

    time.sleep(args.duration_seconds)
    stop_event.set()

    for t in py_threads + cpp_threads:
        t.join(timeout=5)

    if hqt_engine is not None:
        hqt_engine.flush_logs()
        hqt_engine.set_log_callback(None)
        hqt_engine.set_stderr_logging(True)

    adapter.flush()
    adapter.remove(sink_id)
    sink.close()

    integrity = _line_integrity_stats(log_file)
    expected_min = py_count + cpp_cb_count
    success = integrity["malformed_lines"] == 0 and integrity["total_lines"] >= expected_min and cb_errors == 0

    elapsed = time.perf_counter() - start
    details = {
        "elapsed_seconds": round(elapsed, 3),
        "log_file": str(log_file),
        "python_entries": py_count,
        "cpp_emit_entries": cpp_emit_count,
        "cpp_callback_entries": cpp_cb_count,
        "callback_errors": cb_errors,
        "expected_min_lines": expected_min,
        "integrity": integrity,
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="thread_safe_logging_stress", success=success, details=details)


def f02_logging_to_sink_under_load(args: argparse.Namespace, hqt_engine: Any | None) -> TestResult:
    _header("f02_logging_to_sink_under_load")
    logs_dir = ROOT_DIR / "artifacts" / "perf" / "logger" / "sink_load"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "sink_under_load.log"
    if log_file.exists():
        log_file.unlink()

    adapter = _make_perf_adapter("perf_sink_load")
    sink = _SizeAndTimeRotatingFileSink(log_file, max_bytes=50 * 1024 * 1024, backup_count=3)
    sink_id = adapter.add(sink, level="DEBUG", format="{time}|{level_plain}|{message}")

    load_seconds = max(1.0, args.load_minutes * 60.0)
    target_per_sec = max(1, int(args.rate_per_minute / 60))
    total_threads = max(1, args.py_threads + args.cpp_threads)
    per_thread_target = max(1, target_per_sec // total_threads)
    stop_event = threading.Event()

    lock = threading.Lock()
    py_logged = 0
    cpp_logged = 0
    critical_logged = 0

    def paced_sleep(start_ts: float, sent: int) -> None:
        expected = sent / per_thread_target
        delay = expected - (time.perf_counter() - start_ts)
        if delay > 0:
            time.sleep(min(delay, 0.05))

    def py_worker(tid: int) -> None:
        nonlocal py_logged, critical_logged
        start_ts = time.perf_counter()
        sent = 0
        while not stop_event.is_set():
            level = "CRITICAL" if (sent % 100 == 0) else "INFO"
            if level == "CRITICAL":
                adapter.critical(f"PY|t={tid}|n={sent}|critical=true")
                with lock:
                    critical_logged += 1
            else:
                adapter.info(f"PY|t={tid}|n={sent}|tick=true")
            sent += 1
            with lock:
                py_logged += 1
            paced_sleep(start_ts, sent)

    cpp_threads: list[threading.Thread] = []
    if hqt_engine is not None:
        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")

        def cpp_callback(level: str, message: str) -> None:
            nonlocal cpp_logged, critical_logged
            lvl = "CRITICAL" if level.lower() == "critical" else "INFO"
            if lvl == "CRITICAL":
                adapter.critical(f"CPP|lvl={level}|{message}")
                with lock:
                    critical_logged += 1
            else:
                adapter.info(f"CPP|lvl={level}|{message}")
            with lock:
                cpp_logged += 1

        hqt_engine.set_log_callback(cpp_callback)

        def cpp_worker(tid: int) -> None:
            start_ts = time.perf_counter()
            sent = 0
            while not stop_event.is_set():
                lvl = "fatal" if (sent % 100 == 0) else "info"
                hqt_engine.emit_log(lvl, f"t={tid}|n={sent}|tick=true")
                sent += 1
                paced_sleep(start_ts, sent)

        cpp_threads = [threading.Thread(target=cpp_worker, args=(i,), daemon=True) for i in range(args.cpp_threads)]
    else:
        print("[f02] hqt_engine unavailable: C++ load path skipped.")

    py_threads = [threading.Thread(target=py_worker, args=(i,), daemon=True) for i in range(args.py_threads)]

    start = time.perf_counter()
    for t in py_threads + cpp_threads:
        t.start()

    time.sleep(load_seconds)
    stop_event.set()

    for t in py_threads + cpp_threads:
        t.join(timeout=5)

    if hqt_engine is not None:
        hqt_engine.flush_logs()
        hqt_engine.set_log_callback(None)
        hqt_engine.set_stderr_logging(True)

    adapter.flush()
    adapter.remove(sink_id)
    sink.close()

    elapsed = time.perf_counter() - start
    integrity = _line_integrity_stats(log_file)
    observed_rate = (py_logged + cpp_logged) / elapsed if elapsed > 0 else 0

    # Ensure every CRITICAL marker made it to file.
    content = log_file.read_text(encoding="utf-8", errors="replace")
    critical_in_file = sum(1 for line in content.splitlines() if "|CRITICAL|" in line)

    success = (
        integrity["malformed_lines"] == 0
        and critical_in_file >= int(critical_logged * 0.98)
        and observed_rate >= max(50, target_per_sec * 0.5)
    )

    details = {
        "elapsed_seconds": round(elapsed, 3),
        "log_file": str(log_file),
        "target_rate_per_sec": target_per_sec,
        "observed_rate_per_sec": round(observed_rate, 2),
        "python_logged": py_logged,
        "cpp_logged_via_callback": cpp_logged,
        "critical_expected": critical_logged,
        "critical_found_in_file": critical_in_file,
        "integrity": integrity,
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="logging_to_sink_under_load", success=success, details=details)


def f03_rotation_under_load(args: argparse.Namespace) -> TestResult:
    _header("f03_rotation_under_load")
    logs_dir = ROOT_DIR / "artifacts" / "perf" / "logger" / "rotation"
    logs_dir.mkdir(parents=True, exist_ok=True)
    base_file = logs_dir / "rotation_under_load.log"

    for f in logs_dir.glob("rotation_under_load.log*"):
        try:
            f.unlink()
        except Exception:
            pass

    adapter = _make_perf_adapter("perf_rotation")
    sink = _SizeAndTimeRotatingFileSink(
        base_file,
        max_bytes=max(4096, args.rotation_size_bytes),
        backup_count=max(2, args.rotation_backups),
    )
    sink_id = adapter.add(sink, level="INFO", format="{time}|{level_plain}|{message}")

    stop_event = threading.Event()

    def writer(tid: int) -> None:
        n = 0
        while not stop_event.is_set():
            payload = "X" * 400
            adapter.info(f"ROT|t={tid}|n={n}|payload={payload}")
            n += 1

    threads = [threading.Thread(target=writer, args=(i,), daemon=True) for i in range(max(2, args.py_threads // 2))]
    for t in threads:
        t.start()

    time.sleep(8 if not args.quick else 3)
    stop_event.set()
    for t in threads:
        t.join(timeout=5)

    adapter.flush()
    adapter.remove(sink_id)
    sink.close()

    files = sorted(logs_dir.glob("rotation_under_load.log*"))
    total_lines = 0
    unreadable = 0
    for f in files:
        try:
            total_lines += len(f.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            unreadable += 1

    success = len(files) >= 2 and unreadable == 0 and total_lines > 0
    details = {
        "base_file": str(base_file),
        "files_found": [str(f) for f in files],
        "file_count": len(files),
        "total_lines": total_lines,
        "unreadable_files": unreadable,
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="rotation_under_load", success=success, details=details)


def f04_component_filtering_concurrency(args: argparse.Namespace) -> TestResult:
    _header("f04_component_filtering_concurrency")
    logs_dir = ROOT_DIR / "artifacts" / "perf" / "logger" / "component_filter"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "component_filter.log"
    if log_file.exists():
        log_file.unlink()

    adapter = _make_perf_adapter("perf_filter")
    sink = _SizeAndTimeRotatingFileSink(log_file, max_bytes=10 * 1024 * 1024, backup_count=2)
    sink_id = adapter.add(sink, level="INFO", format="{time}|{level_plain}|{message}")

    adapter.set_min_level("ERROR")
    adapter.set_component_level("risk", "INFO")

    stop_event = threading.Event()
    counters = {"risk_info": 0, "trade_info": 0}
    lock = threading.Lock()

    def writer(component: str) -> None:
        key = f"{component}_info"
        n = 0
        while not stop_event.is_set():
            adapter.info(f"CMP|component={component}|n={n}", component=component)
            n += 1
            with lock:
                counters[key] += 1

    threads = [
        threading.Thread(target=writer, args=("risk",), daemon=True),
        threading.Thread(target=writer, args=("trade",), daemon=True),
    ]

    for t in threads:
        t.start()

    time.sleep(5 if not args.quick else 2)
    stop_event.set()
    for t in threads:
        t.join(timeout=5)

    adapter.clear_component_level("risk")
    adapter.set_min_level("TRACE")
    adapter.flush()
    adapter.remove(sink_id)
    sink.close()

    content = log_file.read_text(encoding="utf-8", errors="replace")
    risk_count = content.count("component=risk")
    trade_count = content.count("component=trade")

    success = risk_count > 0 and trade_count == 0
    details = {
        "attempted_risk_info": counters["risk_info"],
        "attempted_trade_info": counters["trade_info"],
        "file_risk_entries": risk_count,
        "file_trade_entries": trade_count,
        "log_file": str(log_file),
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="component_filtering_concurrency", success=success, details=details)


def main() -> None:
    args = _build_parser()
    if args.quick:
        args.duration_seconds = min(args.duration_seconds, 6)
        args.load_minutes = min(args.load_minutes, 0.2)
        args.py_threads = min(args.py_threads, 4)
        args.cpp_threads = min(args.cpp_threads, 4)
        args.rate_per_minute = min(args.rate_per_minute, 10_000)

    hqt_engine = _safe_import_hqt_engine()

    # Toggle sections by commenting/uncommenting calls below.
    results = [
        f01_thread_safe_logging_stress_test(args, hqt_engine),
        f02_logging_to_sink_under_load(args, hqt_engine),
        f03_rotation_under_load(args),
        f04_component_filtering_concurrency(args),
    ]

    passed = sum(1 for r in results if r.success)
    report_path = _write_report(results, args)

    print("\n" + "=" * 72)
    print(f"[LOGGER PERF] Summary: {passed}/{len(results)} tests passed")
    for r in results:
        status = "PASS" if r.success else "FAIL"
        print(f"- {status} {r.name}")
    print(f"[LOGGER PERF] Report: {report_path}")

    # Non-zero exit if any scenario fails.
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

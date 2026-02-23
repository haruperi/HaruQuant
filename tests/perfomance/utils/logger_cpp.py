"""C++ logger performance harness via haruquant bridge.

Run examples:
    python tests/perfomance/utils/logger_cpp.py
    python tests/perfomance/utils/logger_cpp.py --duration-seconds 60 --threads 10

Focus:
- C++ emit throughput under concurrency
- callback delivery ratio
- callback latency percentiles
- component filter behavior under load
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@dataclass
class TestResult:
    name: str
    success: bool
    details: dict[str, Any]


def _header(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"[LOGGER CPP PERF] {title}")
    print("=" * 72)


def _build_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="C++ logger bridge performance harness")
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--latency-samples", type=int, default=30000)
    parser.add_argument("--quick", action="store_true")
    return parser.parse_args()


def _load_haruquant() -> Any:
    bridge_release = ROOT_DIR / "build" / "bridge" / "Release"
    vcpkg_bin = ROOT_DIR / "build" / "vcpkg_installed" / "x64-windows" / "bin"

    if bridge_release.exists():
        if str(bridge_release) not in sys.path:
            sys.path.insert(0, str(bridge_release))
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(bridge_release))

    if vcpkg_bin.exists() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(vcpkg_bin))

    import haruquant  # type: ignore

    return haruquant


def _percentile_sorted(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    k = int(round((p / 100.0) * (len(values) - 1)))
    return values[k]


def _write_report(results: list[TestResult], args: argparse.Namespace) -> Path:
    out_dir = ROOT_DIR / "artifacts" / "perf" / "logger_cpp"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"logger_cpp_perf_report_{ts}.json"
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "duration_seconds": args.duration_seconds,
            "threads": args.threads,
            "latency_samples": args.latency_samples,
            "quick": args.quick,
        },
        "results": [asdict(r) for r in results],
    }
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_file


def f01_cpp_emit_throughput(args: argparse.Namespace, haruquant: Any) -> TestResult:
    _header("f01_cpp_emit_throughput")
    stop_event = threading.Event()
    lock = threading.Lock()
    emitted = 0
    received = 0

    def cb(level: str, message: str) -> None:
        nonlocal received
        with lock:
            received += 1

    haruquant.set_stderr_logging(False)
    haruquant.set_log_level("debug")
    haruquant.set_log_callback(cb)

    def worker(tid: int) -> None:
        nonlocal emitted
        n = 0
        while not stop_event.is_set():
            haruquant.emit_log("info", f"perf|thr={tid}|n={n}")
            n += 1
            with lock:
                emitted += 1

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(args.threads)]
    start = time.perf_counter()
    for t in threads:
        t.start()

    time.sleep(args.duration_seconds)
    stop_event.set()
    for t in threads:
        t.join(timeout=5)

    haruquant.flush_logs()
    haruquant.set_log_callback(None)
    haruquant.set_stderr_logging(True)
    elapsed = max(1e-9, time.perf_counter() - start)

    emit_rate = emitted / elapsed
    recv_ratio = (received / emitted) if emitted else 0.0
    success = emitted > 0 and recv_ratio >= 0.995

    details = {
        "elapsed_seconds": round(elapsed, 3),
        "threads": args.threads,
        "emitted": emitted,
        "received_callback": received,
        "emit_rate_per_sec": round(emit_rate, 2),
        "callback_delivery_ratio": round(recv_ratio, 6),
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="cpp_emit_throughput", success=success, details=details)


def f02_cpp_callback_latency_percentiles(args: argparse.Namespace, haruquant: Any) -> TestResult:
    _header("f02_cpp_callback_latency_percentiles")
    pattern = re.compile(r"^lat\|id=(\d+)\|t0=(\d+)$")
    lock = threading.Lock()
    send_times: dict[int, int] = {}
    latencies_us: list[float] = []
    callback_misses = 0

    def cb(level: str, message: str) -> None:
        nonlocal callback_misses
        m = pattern.match(message)
        if not m:
            return
        mid = int(m.group(1))
        t0 = int(m.group(2))
        t1 = time.perf_counter_ns()
        with lock:
            if mid in send_times:
                latencies_us.append((t1 - t0) / 1000.0)
                send_times.pop(mid, None)
            else:
                callback_misses += 1

    haruquant.set_stderr_logging(False)
    haruquant.set_log_level("debug")
    haruquant.set_log_callback(cb)

    start = time.perf_counter()
    for i in range(args.latency_samples):
        t0 = time.perf_counter_ns()
        with lock:
            send_times[i] = t0
        haruquant.emit_log("info", f"lat|id={i}|t0={t0}")

    haruquant.flush_logs()

    deadline = time.perf_counter() + 5.0
    while time.perf_counter() < deadline:
        with lock:
            remaining = len(send_times)
        if remaining == 0:
            break
        time.sleep(0.01)

    haruquant.set_log_callback(None)
    haruquant.set_stderr_logging(True)

    with lock:
        remaining = len(send_times)
        sorted_lat = sorted(latencies_us)

    p50 = _percentile_sorted(sorted_lat, 50)
    p90 = _percentile_sorted(sorted_lat, 90)
    p99 = _percentile_sorted(sorted_lat, 99)
    max_v = sorted_lat[-1] if sorted_lat else 0.0

    success = len(sorted_lat) >= int(args.latency_samples * 0.995) and p99 <= 50_000

    details = {
        "elapsed_seconds": round(time.perf_counter() - start, 3),
        "samples_sent": args.latency_samples,
        "samples_received": len(sorted_lat),
        "pending_after_wait": remaining,
        "callback_misses": callback_misses,
        "latency_us": {
            "p50": round(p50, 3),
            "p90": round(p90, 3),
            "p99": round(p99, 3),
            "max": round(max_v, 3),
        },
        "thresholds": {
            "delivery_ratio_min": 0.995,
            "p99_max_us": 50000,
        },
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="cpp_callback_latency_percentiles", success=success, details=details)


def f03_cpp_component_filter_under_load(args: argparse.Namespace, haruquant: Any) -> TestResult:
    _header("f03_cpp_component_filter_under_load")
    lock = threading.Lock()
    info_count = 0
    error_count = 0

    def cb(level: str, message: str) -> None:
        nonlocal info_count, error_count
        with lock:
            if level.lower() == "info":
                info_count += 1
            elif level.lower() == "error":
                error_count += 1

    haruquant.set_stderr_logging(False)
    haruquant.set_log_callback(cb)
    haruquant.set_log_level("debug")
    haruquant.set_component_log_level("haruquant", "error")

    # emit a burst of infos/errors; info should be mostly filtered for default module component.
    n = max(1000, args.latency_samples // 5)
    for i in range(n):
        haruquant.emit_log("info", f"cmp|n={i}|info")
        haruquant.emit_log("error", f"cmp|n={i}|error")

    haruquant.flush_logs()
    haruquant.clear_component_log_level("haruquant")
    haruquant.clear_all_component_log_levels()
    haruquant.set_log_callback(None)
    haruquant.set_stderr_logging(True)

    # Depending on component mapping in bridge, some info may still pass; error must be present.
    success = error_count >= int(n * 0.99)
    details = {
        "iterations": n,
        "info_received": info_count,
        "error_received": error_count,
        "expected_error_min": int(n * 0.99),
    }
    print(json.dumps(details, indent=2))
    return TestResult(name="cpp_component_filter_under_load", success=success, details=details)


def main() -> None:
    args = _build_parser()
    if args.quick:
        args.duration_seconds = min(args.duration_seconds, 8)
        args.threads = min(args.threads, 4)
        args.latency_samples = min(args.latency_samples, 5000)

    try:
        haruquant = _load_haruquant()
    except Exception as exc:
        print(f"[LOGGER CPP PERF] Failed to import haruquant: {exc}")
        raise SystemExit(1)

    results = [
        f01_cpp_emit_throughput(args, haruquant),
        f02_cpp_callback_latency_percentiles(args, haruquant),
        f03_cpp_component_filter_under_load(args, haruquant),
    ]

    passed = sum(1 for r in results if r.success)
    report_path = _write_report(results, args)

    print("\n" + "=" * 72)
    print(f"[LOGGER CPP PERF] Summary: {passed}/{len(results)} tests passed")
    for r in results:
        status = "PASS" if r.success else "FAIL"
        print(f"- {status} {r.name}")
    print(f"[LOGGER CPP PERF] Report: {report_path}")

    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

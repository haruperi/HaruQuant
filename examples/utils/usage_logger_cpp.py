"""Comprehensive Python + C++ logger usage examples.

Run:
    python examples/utils/logger_cpp.py

This script demonstrates:
- Structlog adapter usage (`apps.utils.logger`)
- C++ spdlog bridge usage (`haruquant`)
- Unified logging feature patterns across both stacks

Tip:
    Comment/uncomment function calls in main() to run only the sections you want.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import io
import os
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.utils.logger import logger


@dataclass
class CppBridgeState:
    available: bool
    module: Any | None


def _header(title: str) -> None:
    print()
    print("=" * 60)
    print(f"[LOGGER EXAMPLE - CPP] {title}")
    print("=" * 60)
    print()


def _load_haruquant() -> CppBridgeState:
    bridge_release_dir = ROOT_DIR / "build" / "bridge" / "Release"
    vcpkg_bin_dir = ROOT_DIR / "build" / "vcpkg_installed" / "x64-windows" / "bin"

    if bridge_release_dir.exists():
        if str(bridge_release_dir) not in sys.path:
            sys.path.insert(0, str(bridge_release_dir))
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(bridge_release_dir))

    if vcpkg_bin_dir.exists() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(vcpkg_bin_dir))

    try:
        import haruquant  # type: ignore

        return CppBridgeState(available=True, module=haruquant)
    except Exception as exc:
        print(f"[LOGGER CPP EXAMPLE] haruquant unavailable: {exc}")
        return CppBridgeState(available=False, module=None)


def f01_structlog_basic_usage() -> None:
    _header("f01_structlog_basic_usage")
    logger.trace("py trace")
    logger.debug("py debug")
    logger.info("py info")
    logger.warning("py warning")
    logger.error("py error")
    logger.critical("py critical")
    print("Python adapter emitted all standard levels.")


def f02_structlog_context_and_binding() -> None:
    _header("f02_structlog_context_and_binding")
    trade_log = logger.bind(component="trade", strategy="breakout", run_id="RUN-CPP-001")
    trade_log.info("strategy initialized", symbol="EURUSD")

    with logger.contextualize(component="risk", correlation_id="CID-CPP-001") as risk_log:
        risk_log.warning("risk nearing limit", max_positions=5, current_positions=4)

    print("Python adapter bind/contextualize usage completed.")


def f03_structlog_sink_callback_capture() -> None:
    _header("f03_structlog_sink_callback_capture")
    captured: list[dict[str, str]] = []

    def sink(record):
        captured.append(
            {
                "level": record.level.name,
                "message": record.message,
                "component": str(record.extra.get("component", "")),
            }
        )

    sink_id = logger.add(sink, raw=True, level="INFO")
    try:
        logger.info("py callback info", component="adapter")
        logger.error("py callback error", component="adapter")
        print(f"Captured {len(captured)} Python records through callback sink.")
    finally:
        logger.remove(sink_id)


def f04_structlog_runtime_filtering() -> None:
    _header("f04_structlog_runtime_filtering")
    original = logger.get_min_level()
    logger.set_min_level("ERROR")
    logger.set_component_level("risk", "INFO")

    logger.info("filtered by global threshold", component="trade")
    logger.info("allowed by component override", component="risk")
    logger.error("always allowed at ERROR", component="trade")

    logger.clear_component_level("risk")
    logger.set_min_level(original)
    print("Python runtime filtering and per-component override demonstrated.")


def f05_cpp_bridge_basic_usage(bridge: CppBridgeState) -> None:
    _header("f05_cpp_bridge_basic_usage")
    if not bridge.available:
        print("Skipped: haruquant not available.")
        return

    haruquant = bridge.module
    haruquant.set_log_level("debug")
    haruquant.emit_log("info", "cpp info message")
    haruquant.emit_log("warn", "cpp warn alias message")
    haruquant.emit_log("fatal", "cpp fatal alias message")
    haruquant.flush_logs()
    print("C++ bridge emitted info/warn/fatal levels and flushed logs.")


def f06_cpp_bridge_component_filtering(bridge: CppBridgeState) -> None:
    _header("f06_cpp_bridge_component_filtering")
    if not bridge.available:
        print("Skipped: haruquant not available.")
        return

    haruquant = bridge.module
    haruquant.set_log_level("debug")
    haruquant.set_component_log_level("haruquant", "error")

    haruquant.emit_log("info", "cpp info likely filtered for haruquant component")
    haruquant.emit_log("error", "cpp error should pass component override")

    haruquant.clear_component_log_level("haruquant")
    haruquant.clear_all_component_log_levels()
    haruquant.flush_logs()
    print("C++ component-level filtering controls exercised.")


def f07_cpp_bridge_callback_capture(bridge: CppBridgeState) -> None:
    _header("f07_cpp_bridge_callback_capture")
    if not bridge.available:
        print("Skipped: haruquant not available.")
        return

    haruquant = bridge.module
    captured: list[tuple[str, str]] = []

    def cb(level: str, message: str) -> None:
        captured.append((level, message))

    haruquant.set_stderr_logging(False)
    haruquant.set_log_callback(cb)
    try:
        haruquant.set_log_level("debug")
        haruquant.emit_log("info", "cpp callback info")
        haruquant.emit_log("error", "cpp callback error")
        haruquant.flush_logs()
        print(f"Captured {len(captured)} C++ callback records.")
    finally:
        haruquant.set_log_callback(None)
        haruquant.set_stderr_logging(True)


def f08_cpp_bridge_usage_example_api(bridge: CppBridgeState) -> None:
    _header("f08_cpp_bridge_usage_example_api")
    if not bridge.available:
        print("Skipped: haruquant not available.")
        return

    haruquant = bridge.module
    if not hasattr(haruquant, "run_cpp_logger_usage_example"):
        print("Skipped: run_cpp_logger_usage_example() not available in loaded bridge.")
        return

    haruquant.run_cpp_logger_usage_example()
    haruquant.flush_logs()
    print("Executed bridge-provided C++ logger usage example.")


def f09_unified_alias_levels(bridge: CppBridgeState) -> None:
    _header("f09_unified_alias_levels")
    logger.log("warn", "python warn alias")
    logger.log("fatal", "python fatal alias")

    if bridge.available:
        haruquant = bridge.module
        haruquant.emit_log("warn", "cpp warn alias")
        haruquant.emit_log("fatal", "cpp fatal alias")
        haruquant.flush_logs()

    print("Alias normalization exercised for Python and C++ logger paths.")


def f10_unified_correlation_pattern(bridge: CppBridgeState) -> None:
    _header("f10_unified_correlation_pattern")
    corr = "CORR-UNIFIED-001"
    run_id = "RUN-UNIFIED-001"
    trace_id = "TRACE-UNIFIED-001"

    py_log = logger.bind(correlation_id=corr, run_id=run_id, trace_id=trace_id, component="unified")
    py_log.info("python side correlated event")

    if bridge.available:
        haruquant = bridge.module
        captured: list[tuple[str, str]] = []

        def cb(level: str, message: str) -> None:
            captured.append((level, message))

        haruquant.set_log_callback(cb)
        try:
            haruquant.emit_log("info", f"cpp side correlated event correlation_id={corr} run_id={run_id} trace_id={trace_id}")
            haruquant.flush_logs()
            print(f"Captured {len(captured)} C++ correlated callback records.")
        finally:
            haruquant.set_log_callback(None)
    else:
        print("C++ correlation callback section skipped (bridge unavailable).")

    print("Unified correlation pattern demonstrated.")


def f11_unified_flush_and_cleanup(bridge: CppBridgeState) -> None:
    _header("f11_unified_flush_and_cleanup")
    logger.flush()
    logger.clear_all_component_levels()
    logger.set_min_level("TRACE")

    if bridge.available:
        haruquant = bridge.module
        if hasattr(haruquant, "clear_all_component_log_levels"):
            haruquant.clear_all_component_log_levels()
        if hasattr(haruquant, "set_stderr_logging"):
            haruquant.set_stderr_logging(True)
        if hasattr(haruquant, "set_log_callback"):
            haruquant.set_log_callback(None)
        if hasattr(haruquant, "flush_logs"):
            haruquant.flush_logs()

    print("Reset Python and C++ logging controls to safe defaults.")


def f12_optional_stringio_formatted_sink() -> None:
    _header("f12_optional_stringio_formatted_sink")
    stream = io.StringIO()
    sink_id = logger.add(stream, level="INFO", format="{time} | {level_plain} | {message}")
    try:
        logger.info("formatted sink line one")
        logger.error("formatted sink line two")
        logger.flush()
        lines = [line for line in stream.getvalue().splitlines() if line.strip()]
        print(f"StringIO formatted sink captured {len(lines)} lines.")
    finally:
        logger.remove(sink_id)


def main() -> None:
    bridge = _load_haruquant()

    # Toggle sections by commenting/uncommenting calls below.
    f01_structlog_basic_usage()
    f02_structlog_context_and_binding()
    f03_structlog_sink_callback_capture()
    f04_structlog_runtime_filtering()
    f05_cpp_bridge_basic_usage(bridge)
    f06_cpp_bridge_component_filtering(bridge)
    f07_cpp_bridge_callback_capture(bridge)
    f08_cpp_bridge_usage_example_api(bridge)
    f09_unified_alias_levels(bridge)
    f10_unified_correlation_pattern(bridge)
    f11_unified_flush_and_cleanup(bridge)
    f12_optional_stringio_formatted_sink()

    print("\n[LOGGER CPP EXAMPLE] Done.")


if __name__ == "__main__":
    main()

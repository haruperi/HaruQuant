"""Comprehensive usage examples for services.utils.logger.

Run:
    python backend/scripts/examples/utils/logger_py.py

Tip:
    Comment/uncomment function calls in main() to run only the sections you want.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.utils.logger import logger


LOG_DIR = ROOT_DIR / "backend" / "logs"


def _header(title: str) -> None:
    print()
    print("=" * 60)
    print(f"[LOGGER EXAMPLE - Python] {title}")
    print("=" * 60)
    print()


def f01_basic_usage() -> None:
    _header("01_basic_usage")
    logger.trace("trace message")
    logger.debug("debug message")
    logger.info("info message")
    logger.success("success message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    print("Emitted all standard levels.")


def f02_formatting_and_fields() -> None:
    _header("02_formatting_and_fields")
    logger.info("Order {order_id} accepted at price={price}", order_id=1001, price=1.2345)
    logger.info(
        "Structured field example",
        component="trade",
        symbol="EURUSD",
        timeframe="M5",
    )
    print("Logged formatted message and structured fields.")


def f03_bind_usage() -> None:
    _header("03_bind_usage")
    trade_log = logger.bind(component="trade", strategy="mean_reversion", run_id="RUN-001")
    trade_log.info("Strategy started")
    trade_log.warning("Spread widened", symbol="EURUSD", spread_points=18)
    print("Used logger.bind(...) to reuse shared context.")


def f04_contextualize_usage() -> None:
    _header("04_contextualize_usage")
    with logger.contextualize(component="risk", correlation_id="CID-ABC-123") as log:
        log.info("Risk check started")
        log.error("Risk threshold breached", max_positions=5, current_positions=8)
    print("Used logger.contextualize(...) for scoped context.")


def f05_global_level_filtering() -> None:
    _header("05_global_level_filtering")
    original = logger.get_min_level()
    logger.set_min_level("WARNING")
    logger.info("This info should be filtered at WARNING min level")
    logger.warning("This warning should be emitted")
    logger.set_min_level(original)
    print(f"Temporarily set min level to WARNING, then restored to {original}.")


def f06_component_level_filtering() -> None:
    _header("06_component_level_filtering")
    original = logger.get_min_level()
    logger.set_min_level("ERROR")
    logger.set_component_level("risk", "INFO")

    logger.info("Filtered by global ERROR level", component="trade")
    logger.info("Allowed by risk override", component="risk")

    logger.clear_component_level("risk")
    logger.set_min_level(original)
    print("Demonstrated per-component override against stricter global level.")


def f07_custom_sink_stringio() -> None:
    _header("07_custom_sink_stringio")
    stream = io.StringIO()
    sink_id = logger.add(
        stream,
        level="INFO",
        format="{time} | {level_plain} | {name} | {message}",
    )
    try:
        logger.info("Captured into in-memory sink", component="example")
        logger.error("Another captured line", component="example")
        logger.flush()
        captured = stream.getvalue().strip().splitlines()
        print(f"Captured {len(captured)} lines in StringIO sink.")
    finally:
        logger.remove(sink_id)


def f08_custom_raw_callback_sink() -> None:
    _header("08_custom_raw_callback_sink")
    records: list[dict[str, str]] = []

    def on_record(record):
        records.append(
            {
                "level": record.level.name,
                "message": record.message,
                "component": str(record.extra.get("component", "")),
            }
        )

    sink_id = logger.add(on_record, raw=True, level="INFO")
    try:
        logger.info("Callback sink record", component="callback")
        logger.error("Callback sink error", component="callback")
        print(f"Raw callback captured {len(records)} records.")
    finally:
        logger.remove(sink_id)


def f09_access_log_routing() -> None:
    _header("09_access_log_routing")
    logger.info(
        "HTTP request served",
        component="access",
        method="GET",
        path="/health",
        status_code=200,
        remote_addr="127.0.0.1",
    )
    print("Emitted access-style record (routes to default access.log sink).")


def f10_exception_logging() -> None:
    _header("10_exception_logging")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Handled exception example", component="runtime")
    print("Logged exception with traceback metadata.")


def f11_default_file_outputs_check() -> None:
    _header("11_default_file_outputs_check")
    expected = [
        LOG_DIR / "app.log",
        LOG_DIR / "debug.log",
        LOG_DIR / "errors.log",
        LOG_DIR / "access.log",
    ]
    for path in expected:
        status = "exists" if path.exists() else "missing"
        size = path.stat().st_size if path.exists() else 0
        print(f"- {path}: {status}, size={size} bytes")


def f12_cleanup_component_filters() -> None:
    _header("12_cleanup_component_filters")
    logger.clear_all_component_levels()
    logger.set_min_level("TRACE")
    print("Reset logger component overrides and min level to TRACE.")


def main() -> None:
    # Toggle sections by commenting/uncommenting calls below.
    f01_basic_usage()
    f02_formatting_and_fields()
    f03_bind_usage()
    f04_contextualize_usage()
    f05_global_level_filtering()
    f06_component_level_filtering()
    f07_custom_sink_stringio()
    f08_custom_raw_callback_sink()
    f09_access_log_routing()
    f10_exception_logging()
    f11_default_file_outputs_check()
    f12_cleanup_component_filters()

    logger.flush()
    print("\n[LOGGER EXAMPLE] Done.")


if __name__ == "__main__":
    main()



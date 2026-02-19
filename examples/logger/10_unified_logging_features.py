import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.logger import logger

try:
    import hqt_engine  # type: ignore

    HAS_CPP = True
except Exception:
    HAS_CPP = False


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def python_demo() -> None:
    section("Python: IDs, Runtime Filtering, Redaction")
    received = []
    sink_id = logger.add(received.append, level="DEBUG", raw=True)

    try:
        logger.set_min_level("INFO")
        logger.set_component_level("risk", "ERROR")

        scoped = logger.bind(
            component="risk",
            correlation_id="corr-1001",
            run_id="run-20260217",
            trace_id="trace-abc-001",
        )

        scoped.info("Risk info message should be filtered at component level")
        scoped.error(
            "Order rejected password=supersecret token=abcd",
            extra={"api_key": "python-api-key", "safe": "ok"},
        )

        print(f"Captured Python records: {len(received)}")
        if received:
            record = received[-1]
            print(f"Level: {record.level.name}")
            print(f"Message: {record.message}")
            print(
                "IDs:",
                record.correlation_id,
                record.run_id,
                record.trace_id,
            )
            print(f"Extra: {record.extra}")
    finally:
        logger.clear_all_component_levels()
        logger.set_min_level("TRACE")
        logger.remove(sink_id)


def cpp_demo() -> None:
    section("C++: Severity Normalization, Runtime Filtering, Redaction")
    if not HAS_CPP:
        print("hqt_engine not available; skipping C++ demo.")
        return
    required = (
        "set_stderr_logging",
        "set_log_level",
        "set_log_callback",
        "emit_log",
    )
    missing = [name for name in required if not hasattr(hqt_engine, name)]
    if missing:
        print(f"hqt_engine missing required API {missing}; skipping C++ demo.")
        return

    received = []

    def callback(*args):
        if len(args) == 1 and isinstance(args[0], dict):
            received.append(args[0])
            return
        if len(args) == 2:
            level, message = args
            received.append(
                {
                    "level": {"name": str(level)},
                    "message": str(message),
                    "correlation_id": "",
                    "run_id": "",
                    "trace_id": "",
                }
            )

    hqt_engine.set_stderr_logging(False)
    try:
        hqt_engine.set_log_level("warn")
        level_alias_supported = True
    except Exception:
        hqt_engine.set_log_level("warning")
        level_alias_supported = False
    has_component_filter = hasattr(hqt_engine, "set_component_log_level") and hasattr(
        hqt_engine, "clear_all_component_log_levels"
    )
    if has_component_filter:
        hqt_engine.set_component_log_level("module", "error")
    hqt_engine.set_log_callback(callback)

    try:
        hqt_engine.emit_log("warn", "warn should be filtered by component override")
        try:
            hqt_engine.emit_log("fatal", "fatal passes; password=cppsecret token=cpp-token")
            emitted_with = "fatal"
        except Exception:
            hqt_engine.emit_log("error", "error passes; password=cppsecret token=cpp-token")
            emitted_with = "error"
    finally:
        hqt_engine.set_log_callback(None)
        if has_component_filter:
            hqt_engine.clear_all_component_log_levels()

    print(f"Captured C++ records: {len(received)}")
    if received:
        record = received[-1]
        print(f"Level (normalized): {record['level']['name']}")
        print(f"Message (redacted): {record['message']}")
        print(f"C++ alias normalization active: {level_alias_supported}")
        print(f"High-severity emission level used: {emitted_with}")
        print(f"Component runtime filtering active: {has_component_filter}")
        print(
            "IDs present:",
            "correlation_id" in record,
            "run_id" in record,
            "trace_id" in record,
        )


def summary() -> None:
    section("What This Demonstrates")
    print("1. Severity normalization between Python and C++ (warn/fatal aliases).")
    print("2. correlation_id/run_id/trace_id fields in log schema.")
    print("3. Dynamic runtime filtering by severity + component.")
    print("4. Automatic sensitive value redaction in message and metadata.")


def main() -> None:
    section("Unified Logging Features Usage")
    python_demo()
    cpp_demo()
    summary()


if __name__ == "__main__":
    main()

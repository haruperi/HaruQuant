import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

bridge_dir = ROOT / "build" / "bridge" / "Release"
if bridge_dir.exists() and str(bridge_dir) not in sys.path:
    sys.path.insert(0, str(bridge_dir))

try:
    import hqt_engine  # type: ignore
except Exception:
    hqt_engine = None  # type: ignore


def main() -> None:
    print("--- C++ spdlog Bridge Usage ---")
    if hqt_engine is None:
        print("hqt_engine not available. Build C++ bridge first.")
        return

    received = []

    def callback(*args):
        if len(args) == 1 and isinstance(args[0], dict):
            received.append(args[0])
            return
        if len(args) == 2:
            level, message = args
            received.append({"level": {"name": str(level)}, "message": str(message)})

    hqt_engine.set_stderr_logging(False)

    # Severity alias normalization (warn/fatal) with fallback for older bridge builds.
    try:
        hqt_engine.set_log_level("warn")
        print("Global level set using alias: warn")
    except Exception:
        hqt_engine.set_log_level("warning")
        print("Alias warn not supported in this build; used warning")

    has_component_runtime = hasattr(hqt_engine, "set_component_log_level") and hasattr(
        hqt_engine, "clear_all_component_log_levels"
    )
    if has_component_runtime:
        hqt_engine.set_component_log_level("module", "error")
        print("Enabled runtime component filter: module=error")
    else:
        print("Component runtime filtering API not available in this build")

    hqt_engine.set_log_callback(callback)
    try:
        hqt_engine.emit_log("warning", "warning may be filtered by component override")
        try:
            hqt_engine.emit_log("fatal", "fatal event password=cppsecret token=cpp-token")
        except Exception:
            hqt_engine.emit_log("error", "error event password=cppsecret token=cpp-token")
    finally:
        hqt_engine.set_log_callback(None)
        if has_component_runtime:
            hqt_engine.clear_all_component_log_levels()

    print(f"Captured callback records: {len(received)}")
    if received:
        rec = received[-1]
        print(f"Last level: {rec['level']['name']}")
        print(f"Last message: {rec['message']}")
        print("Expected in latest build: secrets redacted in message.")


if __name__ == "__main__":
    main()

"""Run the C++ logger usage example through the Python bridge."""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.logger import logger


def _load_engine():
    root = Path(__file__).resolve().parents[3]
    build_bridge = root / "build" / "bridge" / "Release"
    if build_bridge.exists():
        sys.path.insert(0, str(build_bridge))
    return __import__("hqt_engine")


def main() -> None:
    hqt_engine = _load_engine()

    def on_cpp_log(level: str, message: str) -> None:
        text = f"[C++ usage] {message}"
        lvl = (level or "").upper()
        if lvl == "DEBUG":
            logger.debug(text)
        elif lvl == "WARNING":
            logger.warning(text)
        elif lvl == "ERROR":
            logger.error(text)
        else:
            logger.info(text)

    hqt_engine.set_stderr_logging(False)
    hqt_engine.set_log_level("debug")
    hqt_engine.set_log_callback(on_cpp_log)
    hqt_engine.run_cpp_logger_usage_example()
    hqt_engine.set_log_callback(None)

    logger.success("C++ logger usage example completed")


if __name__ == "__main__":
    main()


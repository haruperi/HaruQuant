"""Tests for the hqt_engine C++ bridge module."""

import sys
from pathlib import Path

import pytest

# Add build output to path so hqt_engine can be imported
_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))

try:
    import hqt_engine

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


class TestHello:
    def test_hello_returns_version_string(self):
        assert hqt_engine.hello() == "HQT Engine v0.1.0"

    def test_version_struct(self):
        v = hqt_engine.version()
        assert v.major == 0
        assert v.minor == 1
        assert v.patch == 0

    def test_version_repr(self):
        v = hqt_engine.version()
        assert repr(v) == "Version(0, 1, 0)"


class TestLoggingBridge:
    def test_logging_controls_are_available(self):
        assert hasattr(hqt_engine, "set_log_level")
        assert hasattr(hqt_engine, "set_stderr_logging")
        assert hasattr(hqt_engine, "set_log_callback")
        assert hasattr(hqt_engine, "emit_log")

    def test_log_callback_receives_cpp_log(self):
        received = []

        def callback(level, message):
            received.append((level, message))

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("info", "bridge test message")

        hqt_engine.set_log_callback(None)

        assert received
        assert received[-1][0] == "INFO"
        assert received[-1][1] == "bridge test message"

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

    def test_sum_smoke_function(self):
        assert hasattr(hqt_engine, "sum")
        assert hqt_engine.sum([1.0, 2.5, 3.5]) == pytest.approx(7.0)
        assert hqt_engine.sum([]) == pytest.approx(0.0)

    def test_sum_dtype_error_maps_to_type_error(self):
        with pytest.raises(TypeError):
            hqt_engine.sum([1.0, "x", 3.0])

    def test_sum_shape_error_maps_to_value_error(self):
        with pytest.raises(ValueError):
            hqt_engine.sum([[1.0, 2.0], [3.0, 4.0]])


class TestLoggingBridge:
    def test_logging_controls_are_available(self):
        assert hasattr(hqt_engine, "set_log_level")
        assert hasattr(hqt_engine, "set_component_log_level")
        assert hasattr(hqt_engine, "clear_component_log_level")
        assert hasattr(hqt_engine, "clear_all_component_log_levels")
        assert hasattr(hqt_engine, "set_stderr_logging")
        assert hasattr(hqt_engine, "set_log_callback")
        assert hasattr(hqt_engine, "emit_log")

    def test_log_callback_receives_structured_cpp_log(self):
        received = []

        def callback(record):
            received.append(record)

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("info", "bridge test message")

        hqt_engine.set_log_callback(None)

        assert received
        record = received[-1]
        assert isinstance(record, dict)
        assert record["level"]["name"] == "INFO"
        assert record["message"] == "bridge test message"
        assert record["module"]
        assert record["function"]
        assert isinstance(record["line"], int)
        assert record["time"]["repr"]
        assert "process" in record
        assert "thread" in record
        assert "correlation_id" in record
        assert "run_id" in record
        assert "trace_id" in record

    def test_log_callback_legacy_signature_still_works(self):
        received = []

        def callback(level, message):
            received.append((level, message))

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("warning", "legacy callback")

        hqt_engine.set_log_callback(None)

        assert received
        assert received[-1][0] == "WARNING"
        assert received[-1][1] == "legacy callback"

    def test_log_level_normalization_supports_warn_and_critical(self):
        received = []

        def callback(record):
            received.append(record)

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("warn")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("critical", "critical callback")

        hqt_engine.set_log_callback(None)

        assert received
        record = received[-1]
        assert record["level"]["name"] == "CRITICAL"
        assert record["message"] == "critical callback"

    def test_log_callback_context_ids_roundtrip(self):
        received = []

        def callback(record):
            received.append(record)

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("info", "ids test")

        hqt_engine.set_log_callback(None)

        assert received
        record = received[-1]
        assert record["correlation_id"] == ""
        assert record["run_id"] == ""
        assert record["trace_id"] == ""
        assert "correlation_id" in record["extra"]
        assert "run_id" in record["extra"]
        assert "trace_id" in record["extra"]

    def test_component_runtime_filtering_cpp_bridge(self):
        received = []

        def callback(record):
            received.append(record)

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_component_log_level("module", "error")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("info", "should-be-filtered")
        hqt_engine.emit_log("error", "should-pass")

        hqt_engine.set_log_callback(None)
        hqt_engine.clear_component_log_level("module")

        assert [r["message"] for r in received] == ["should-pass"]

    def test_cpp_bridge_redacts_sensitive_message_fields(self):
        received = []

        def callback(record):
            received.append(record)

        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_level("debug")
        hqt_engine.set_log_callback(callback)

        hqt_engine.emit_log("error", "login failed password=supersecret token=abcd")

        hqt_engine.set_log_callback(None)

        assert received
        msg = received[-1]["message"]
        assert "supersecret" not in msg
        assert "abcd" not in msg
        assert "***REDACTED***" in msg


class TestErrorTaxonomy:
    def test_error_taxonomy_api_is_available(self):
        assert hasattr(hqt_engine, "error_from_retcode")
        assert hasattr(hqt_engine, "error_name")

    def test_error_from_retcode_returns_structured_payload(self):
        payload = hqt_engine.error_from_retcode(10013)
        assert isinstance(payload, dict)
        assert payload["code"] == 10013
        assert payload["name"] == "TRADE_RETCODE_INVALID"
        assert payload["domain"] == "trade"
        assert isinstance(payload["retryable"], bool)

    def test_error_name_returns_expected_value(self):
        assert hqt_engine.error_name(10014) == "TRADE_RETCODE_INVALID_VOLUME"


class TestSchemaValidationBridge:
    def test_schema_validation_api_is_available(self):
        assert hasattr(hqt_engine, "validate_market_schema")
        assert hasattr(hqt_engine, "validate_trade_schema")
        assert hasattr(hqt_engine, "validate_config_schema")

    def test_validate_market_schema_cpp_bridge(self):
        payload = {
            "symbol": "EURUSD",
            "timestamp": "2026-02-17T13:30:00Z",
            "bid": 1.1000,
            "ask": 1.1002,
            "volume": 1000.0,
        }
        result = hqt_engine.validate_market_schema(payload)
        assert result["ok"] is True

    def test_validate_trade_schema_cpp_bridge_rejects_invalid_side(self):
        payload = {
            "symbol": "EURUSD",
            "side": "HOLD",
            "order_type": "MARKET",
            "volume": 0.1,
        }
        result = hqt_engine.validate_trade_schema(payload)
        assert result["ok"] is False
        assert "side" in result["message"].lower()

    def test_validate_config_schema_cpp_bridge_with_nested_payload(self):
        payload = {
            "mode": "paper",
            "logging": {
                "level": "warn",
                "stderr_enabled": True,
            },
            "risk": {
                "max_positions": 5,
                "max_drawdown_pct": 20.0,
                "max_risk_per_trade_pct": 2.0,
            },
        }
        result = hqt_engine.validate_config_schema(payload)
        assert result["ok"] is True

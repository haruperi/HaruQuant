"""Tests for shared Python/C++ error taxonomy helpers."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from apps.simulation.backend import _translate_cpp_exception
from apps.utils.errors import (
    CppBridgeError,
    CppInvalidRequestError,
    ErrorDescriptor,
    descriptor_from_payload,
    trade_exception_from_descriptor,
)


def test_descriptor_from_payload_defaults() -> None:
    descriptor = descriptor_from_payload(None, fallback_code=10011)
    assert descriptor.code == 10011
    assert descriptor.name == "UNKNOWN"
    assert descriptor.domain == "trade"


def test_trade_exception_from_descriptor_uses_typed_class() -> None:
    descriptor = ErrorDescriptor(
        code=10013,
        name="TRADE_RETCODE_INVALID",
        message="Invalid request",
        domain="trade",
        retryable=False,
    )
    exc = trade_exception_from_descriptor(descriptor, detail="bad request")
    assert isinstance(exc, CppInvalidRequestError)
    assert "code=10013" in str(exc)


def test_translate_cpp_exception_uses_bridge_taxonomy(monkeypatch) -> None:
    fake_bridge = SimpleNamespace(
        error_from_retcode=lambda code: {
            "code": int(code),
            "name": "TRADE_RETCODE_INVALID",
            "message": "Invalid request",
            "domain": "trade",
            "retryable": False,
        }
    )
    monkeypatch.setitem(sys.modules, "hqt_engine", fake_bridge)

    client = SimpleNamespace(last_error=lambda: (10013, "Invalid request"))
    exc = _translate_cpp_exception(RuntimeError("native failure"), client)
    assert isinstance(exc, CppInvalidRequestError)


def test_translate_cpp_exception_falls_back_to_bridge_error() -> None:
    client = SimpleNamespace(last_error=lambda: (1, "Success"))
    exc = _translate_cpp_exception(RuntimeError("boom"), client)
    assert isinstance(exc, CppBridgeError)


def test_translate_cpp_exception_preserves_bridge_typed_exception() -> None:
    BridgeOrderError = type("OrderStateError", (Exception,), {"__module__": "hqt_engine"})
    original = BridgeOrderError("order transition invalid")
    client = SimpleNamespace(last_error=lambda: (10013, "Invalid request"))
    translated = _translate_cpp_exception(original, client)
    assert translated is original

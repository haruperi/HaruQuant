"""Contract tests for C++/Python exception mapping in the bridge."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))
sys.modules.pop("hqt_engine", None)

try:
    import hqt_engine

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


def test_bridge_exports_typed_exception_classes() -> None:
    assert hasattr(hqt_engine, "BridgeError")
    assert hasattr(hqt_engine, "OrderStateError")
    assert hasattr(hqt_engine, "TransientConnectivityError")
    assert hasattr(hqt_engine, "FatalEngineError")


def test_raise_exception_for_retcode_maps_to_order_error() -> None:
    with pytest.raises(hqt_engine.OrderStateError):
        hqt_engine.raise_exception_for_retcode(10013, "invalid request")


def test_raise_exception_for_retcode_maps_retryable_to_transient() -> None:
    with pytest.raises(hqt_engine.TransientConnectivityError):
        hqt_engine.raise_exception_for_retcode(10031, "server connection lost")


def test_raise_exception_for_category_uses_explicit_type() -> None:
    with pytest.raises(hqt_engine.RiskViolationError):
        hqt_engine.raise_exception_for_category("risk", "max drawdown breached")

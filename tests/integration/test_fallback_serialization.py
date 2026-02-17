"""Integration tests for Arrow/Protobuf fallback transfer helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from apps.utils.bridge_transfer import sum_with_fallback

_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))

try:
    import hqt_engine  # noqa: F401

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


def test_sum_with_fallback_auto() -> None:
    payload = sum_with_fallback([1.0, 2.5, 3.5], serialization="auto")
    assert payload["path"] in {"zero_copy", "copy_fallback"}
    assert float(payload["total"]) == pytest.approx(7.0)


def test_sum_with_fallback_arrow_optional() -> None:
    pytest.importorskip("pyarrow")
    payload = sum_with_fallback(np.asarray([1.0, 2.0], dtype=np.float64), serialization="arrow")
    assert payload["path"] == "arrow_fallback"
    assert float(payload["total"]) == pytest.approx(3.0)


def test_sum_with_fallback_protobuf_optional() -> None:
    pytest.importorskip("google.protobuf")
    payload = sum_with_fallback(np.asarray([1.0, 2.0], dtype=np.float64), serialization="protobuf")
    assert payload["path"] == "protobuf_fallback"
    assert float(payload["total"]) == pytest.approx(3.0)

"""Contract tests for zero-copy vs copy fallback transfer paths."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))

try:
    import hqt_engine

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


def test_sum_auto_zero_copy_path() -> None:
    arr = np.asarray([1.0, 2.0, 3.0], dtype=np.float64)
    payload = hqt_engine.sum_auto(arr)
    assert payload["path"] == "zero_copy"
    assert float(payload["total"]) == pytest.approx(6.0)


def test_sum_auto_copy_fallback_path_for_list() -> None:
    payload = hqt_engine.sum_auto([1.0, 2.0, 3.0])
    assert payload["path"] == "copy_fallback"
    assert float(payload["total"]) == pytest.approx(6.0)


def test_bridge_transfer_capabilities() -> None:
    caps = hqt_engine.bridge_transfer_capabilities()
    assert caps["zero_copy"] is True
    assert "arrow_optional" in list(caps["fallbacks"])

"""Contract tests for nanobind module skeleton and lifecycle (IP-18)."""

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


def test_nanobind_module_imports_and_lifecycle_hooks_exist() -> None:
    assert hasattr(hqt_engine, "initialize")
    assert hasattr(hqt_engine, "teardown")
    assert hasattr(hqt_engine, "health_check")

    assert hqt_engine.initialize() is True
    health = hqt_engine.health_check()
    assert isinstance(health, dict)
    assert health["ok"] is True
    assert health["module"] == "hqt_engine"
    assert "initialized" in health
    assert "init_count" in health
    assert hqt_engine.teardown() is True


def test_required_skeleton_submodules_exist() -> None:
    required = [
        "_event",
        "_data",
        "_risk",
        "_oms",
        "_execution",
        "_backtest",
        "_metrics",
    ]

    for name in required:
        assert hasattr(hqt_engine, name)
        sub = getattr(hqt_engine, name)
        assert hasattr(sub, "health_check")
        health = sub.health_check()
        assert health["ok"] is True
        assert health["component"] == name

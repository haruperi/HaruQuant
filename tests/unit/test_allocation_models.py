from __future__ import annotations

import sys
from pathlib import Path

import pytest

_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))

try:
    from hqt_engine import sim

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


def test_allocator_equal_weight():
    alloc = sim.PortfolioAllocator.equal_weight(["EURUSD", "GBPUSD"], 0.8)
    assert alloc["EURUSD"] == pytest.approx(0.4)
    assert alloc["GBPUSD"] == pytest.approx(0.4)


def test_allocator_risk_parity():
    alloc = sim.PortfolioAllocator.risk_parity({"LOW": 0.01, "HIGH": 0.05}, 1.0)
    assert alloc["LOW"] > alloc["HIGH"]
    assert alloc["LOW"] + alloc["HIGH"] == pytest.approx(1.0)


def test_allocator_custom_and_constraints():
    raw = sim.PortfolioAllocator.custom({"EURUSD": 2.0, "GBPUSD": 1.0, "XAUUSD": 1.0}, 1.0, True)

    constraints = sim.ExposureConstraints()
    constraints.max_total_exposure = 0.9
    constraints.max_symbol_exposure = 0.5
    constraints.max_strategy_exposure = {"trend": 0.7, "carry": 0.5}
    constraints.max_asset_exposure = {"FX": 0.6, "METAL": 0.5}

    constrained = sim.PortfolioAllocator.apply_exposure_constraints(
        raw,
        {"EURUSD": "trend", "GBPUSD": "trend", "XAUUSD": "carry"},
        {"EURUSD": "FX", "GBPUSD": "FX", "XAUUSD": "METAL"},
        constraints,
    )
    assert sum(constrained.values()) <= 0.9 + 1e-9
    assert constrained["EURUSD"] <= 0.5 + 1e-9

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


def test_rebalance_controller_scheduled_and_drift():
    policy = sim.RebalancePolicy()
    policy.schedule_interval_msc = 60000
    policy.drift_threshold = 0.1

    controller = sim.RebalanceController(policy)

    assert controller.should_rebalance(1000, {}, {}) is True
    controller.mark_rebalanced(1000)
    assert controller.should_rebalance(20000, {"EURUSD": 0.45}, {"EURUSD": 0.5}) is False
    assert controller.should_rebalance(20000, {"EURUSD": 0.3}, {"EURUSD": 0.5}) is True
    assert controller.should_rebalance(62000, {"EURUSD": 0.45}, {"EURUSD": 0.5}) is True

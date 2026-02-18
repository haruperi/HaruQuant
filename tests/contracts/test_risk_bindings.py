"""Contract tests for C++ _risk bindings (apps/risk parity migration slice 1)."""

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


def test_risk_submodule_has_health_and_types() -> None:
    risk = hqt_engine._risk
    health = risk.health_check()
    assert health["ok"] is True
    assert hasattr(risk, "RiskLimits")
    assert hasattr(risk, "RiskRegimeDetector")
    assert hasattr(risk, "PositionSizer")
    assert hasattr(risk, "RiskGovernor")
    assert hasattr(risk, "RiskBudgetAllocator")
    assert hasattr(risk, "RiskMode")


def test_regime_detector_returns_normal_or_stress() -> None:
    risk = hqt_engine._risk
    detector = risk.RiskRegimeDetector(1.5, 0.5, 0.1, 10, 5)
    returns_matrix = [[0.001, -0.001] for _ in range(15)] + [[0.1, 0.1] for _ in range(5)]
    state = detector.detect(returns_matrix, [])
    assert state.name in ("NORMAL", "STRESS")


def test_position_sizer_fixed_risk_and_validate() -> None:
    risk = hqt_engine._risk
    cfg = risk.PositionSizingConfig()
    cfg.risk_percent = 1.0
    sizer = risk.PositionSizer("fixed_risk", cfg)
    size = sizer.calculate_size(10000.0, 1.1000, 1.0990, 100000.0)
    assert size == pytest.approx(1.0)

    rounded = risk.validate_position_size(0.237, 0.01, 1.0, 0.01, 0.2, False)
    assert rounded == pytest.approx(0.2)


def test_governor_and_allocator_bindings() -> None:
    risk = hqt_engine._risk

    cfg = risk.RiskGovernorConfig()
    cfg.max_drawdown_frac = 0.1
    cfg.max_gross_exposure = 2.0
    cfg.max_net_exposure = 1.0
    governor = risk.RiskGovernor(cfg)

    state = risk.RiskAccountState()
    state.equity = 9900.0
    state.peak_equity = 10000.0
    state.gross_exposure = 1.0
    state.net_exposure = 0.5
    decision = governor.can_trade(state, 0.2, 0.1)
    assert decision.allowed is True
    assert decision.policy_code == "OK"

    pref = risk.CorrelationPreference()
    pref.target_corr = 0.5
    pref.penalty_strength = 2.0
    allocator = risk.RiskBudgetAllocator(pref)
    target = allocator.compute_target_lots(
        {"EURUSD": 1.0, "GBPUSD": 1.0},
        {"EURUSD": 0.5, "GBPUSD": 0.5},
        {"EURUSD": 0.9, "GBPUSD": 0.1},
    )
    assert set(target.keys()) == {"EURUSD", "GBPUSD"}
    assert target["EURUSD"] < target["GBPUSD"]


def test_mode_specific_policy_codes() -> None:
    risk = hqt_engine._risk

    cfg = risk.RiskGovernorConfig()
    cfg.max_drawdown_frac = 0.1
    cfg.max_gross_exposure = 2.0
    cfg.max_net_exposure = 1.0
    cfg.live_limit_multiplier = 0.9
    cfg.backtest_limit_multiplier = 1.1
    cfg.min_order_size = 0.05
    cfg.max_order_size = 2.0
    cfg.max_margin_utilization = 0.8
    governor = risk.RiskGovernor(cfg)

    state = risk.RiskAccountState()
    state.equity = 9800.0
    state.peak_equity = 10000.0
    state.gross_exposure = 1.7
    state.net_exposure = 0.7

    size_decision = governor.can_trade_with_mode(
        state, 0.01, 0.1, 0.1, 100.0, 1000.0, risk.RiskMode.LIVE
    )
    assert size_decision.allowed is False
    assert size_decision.policy_code == "SIZE_INVALID"

    live_decision = governor.can_trade_with_mode(
        state, 0.1, 0.15, 0.1, 100.0, 1000.0, risk.RiskMode.LIVE
    )
    assert live_decision.allowed is False
    assert live_decision.policy_code == "MAX_GROSS_EXPOSURE"

    backtest_decision = governor.can_trade_with_mode(
        state, 0.1, 0.15, 0.1, 100.0, 1000.0, risk.RiskMode.BACKTEST
    )
    assert backtest_decision.allowed is True
    assert backtest_decision.policy_code == "OK"

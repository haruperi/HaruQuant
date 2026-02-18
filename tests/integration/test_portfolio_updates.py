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


def test_portfolio_state_updates_multi_strategy_multi_symbol():
    state = sim.PortfolioState(10000.0, "USD")

    state.upsert_position("strat_a", "EURUSD", 0.5, 500.0, 20.0)
    state.upsert_position("strat_b", "EURUSD", -0.2, 200.0, -5.0)
    state.upsert_position("strat_b", "GBPUSD", 0.8, 700.0, 15.0)

    snapshot = state.account_snapshot()
    assert snapshot.balance == pytest.approx(10000.0)
    assert snapshot.margin == pytest.approx(1400.0)
    assert snapshot.profit == pytest.approx(30.0)
    assert snapshot.equity == pytest.approx(10030.0)

    by_symbol = state.positions_by_symbol()
    assert by_symbol["EURUSD"].net_volume == pytest.approx(0.3)
    assert by_symbol["EURUSD"].margin == pytest.approx(700.0)
    assert by_symbol["GBPUSD"].net_volume == pytest.approx(0.8)

    by_strategy = state.positions_by_strategy("strat_b")
    assert set(by_strategy.keys()) == {"EURUSD", "GBPUSD"}

    state.apply_realized_pnl("strat_a", "EURUSD", 50.0, commission=2.0, swap=0.0)
    snapshot = state.account_snapshot()
    assert state.total_realized_pnl() == pytest.approx(48.0)
    assert snapshot.balance == pytest.approx(10048.0)
    assert snapshot.equity == pytest.approx(10078.0)

    state.clear_position("strat_b", "EURUSD")
    by_symbol = state.positions_by_symbol()
    assert by_symbol["EURUSD"].net_volume == pytest.approx(0.5)

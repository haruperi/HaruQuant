"""Parity tests between C++ BacktestEngine and C++ VectorizedBacktestEngine (IP-38)."""

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

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ bridge not available")


def _make_client() -> "sim.TradeSimulator":
    client = sim.TradeSimulator()
    info = sim.SymbolInfo()
    info.symbol = "EURUSD"
    info.point = 0.00001
    info.spread = 10
    info.bid = 1.10000
    info.ask = 1.10010
    client.set_symbol_info(info)
    return client


def _bars() -> list["sim.BacktestBarStep"]:
    out: list[sim.BacktestBarStep] = []
    for i, close in enumerate([1.10000, 1.10020, 1.10030, 1.10025, 1.10010], start=1):
        b = sim.BacktestBarStep()
        b.time_msc = i * 1000
        b.close = close
        if i == 1:
            b.entry_signal = 1
        if i == 3:
            b.exit_signal = 1
        if i == 4:
            b.entry_signal = -1
        if i == 5:
            b.exit_signal = -1
        out.append(b)
    return out


def test_event_and_vectorized_match_trade_count_and_balance():
    bars = _bars()

    client_event = _make_client()
    event_engine = sim.BacktestEngine(client_event)
    event_engine.run_trading_timeframe("EURUSD", 0.10, bars)
    event_balance = event_engine.account_snapshot().balance
    event_trades = len(event_engine.completed_trades())

    client_vec = _make_client()
    vec_engine = sim.VectorizedBacktestEngine(client_vec)
    vec_engine.run("EURUSD", 0.10, bars)
    vec_balance = vec_engine.account_snapshot().balance
    vec_trades = vec_engine.total_trades()

    assert vec_engine.processed_bars() == len(bars)
    assert event_trades == vec_trades
    assert event_balance == pytest.approx(vec_balance, abs=1e-5)



"""E2E coverage for C++ event-driven backtest lifecycle callbacks (IP-37)."""

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
    symbol = sim.SymbolInfo()
    symbol.symbol = "EURUSD"
    symbol.point = 0.00001
    symbol.spread = 10
    symbol.bid = 1.10000
    symbol.ask = 1.10010
    client.set_symbol_info(symbol)
    return client


def test_event_runner_lifecycle_path():
    client = _make_client()
    engine = sim.BacktestEngine(client)

    bar_calls: list[int] = []
    tick_calls: list[int] = []
    trade_events: list[str] = []

    engine.set_on_bar_processed(lambda i, b, s: bar_calls.append(i))
    engine.set_on_tick_processed(lambda t, s: tick_calls.append(t.time_msc))
    engine.set_on_trade_event(lambda e, s: trade_events.append(e.event_type))

    bars = []
    for i, close in enumerate([1.10000, 1.10020, 1.10030], start=1):
        b = sim.BacktestBarStep()
        b.time_msc = i * 1000
        b.close = close
        if i == 1:
            b.entry_signal = 1
        if i == 3:
            b.exit_signal = 1
        bars.append(b)

    engine.run_trading_timeframe("EURUSD", 0.10, bars)

    assert bar_calls == [0, 1, 2]
    assert tick_calls == [1000, 2000, 3000]
    assert trade_events == ["open", "close"]




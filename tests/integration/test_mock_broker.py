"""Integration tests for C++ MockBroker and PaperTradingEngine bindings."""

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


def _client_with_symbol() -> "sim.SimulatorClient":
    client = sim.SimulatorClient()
    symbol = sim.SymbolInfoData()
    symbol.symbol = "EURUSD"
    symbol.point = 0.00001
    symbol.spread = 10
    symbol.bid = 1.10000
    symbol.ask = 1.10010
    client.set_symbol_info(symbol)

    tick = sim.SymbolTickData()
    tick.time = 1
    tick.time_msc = 1000
    tick.bid = 1.10000
    tick.ask = 1.10010
    tick.last = 1.10000
    client.set_symbol_tick("EURUSD", tick)
    return client


def test_mock_broker_submit_and_fetch_state():
    broker = sim.MockBroker(_client_with_symbol())
    assert broker.connect() is True

    req = sim.TradeRequest()
    req.action = 1
    req.type = 0
    req.symbol = "EURUSD"
    req.volume = 1.0
    result = broker.submit(req)
    assert result.retcode == 10009

    state = broker.fetch_state()
    assert "EURUSD" in state.positions
    assert state.positions["EURUSD"].net_volume == pytest.approx(1.0)


def test_paper_engine_routes_to_mock_broker():
    broker = sim.MockBroker(_client_with_symbol())
    engine = sim.PaperTradingEngine(broker)
    assert engine.connect() is True

    req = sim.TradeRequest()
    req.action = 5
    req.type = 2
    req.symbol = "EURUSD"
    req.volume = 0.2
    req.price = 1.095
    placed = engine.submit_order(req)
    assert placed.retcode == 10008
    assert placed.order > 0

    canceled = engine.cancel_order(placed.order)
    assert canceled.retcode == 10009


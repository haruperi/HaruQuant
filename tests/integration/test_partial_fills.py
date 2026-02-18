"""Integration tests for IP-36 execution quality and partial-fill tracking."""

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


def _client_with_symbol() -> "sim.TradeSimulator":
    client = sim.TradeSimulator()
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


def _market_buy(volume: float = 1.0) -> "sim.TradeRequest":
    req = sim.TradeRequest()
    req.action = 1
    req.type = 0
    req.symbol = "EURUSD"
    req.volume = volume
    return req


def test_twap_schedule():
    slices = sim.ExecutionAlgoTWAP.build_schedule(1.0, 0, 3000, 4)
    assert len(slices) == 4
    assert sum(s.volume for s in slices) == pytest.approx(1.0)
    assert slices[0].scheduled_time_ms == 0
    assert slices[-1].scheduled_time_ms == 3000


def test_vwap_schedule():
    slices = sim.ExecutionAlgoVWAP.build_schedule(1.0, 0, 3000, [1.0, 2.0, 3.0, 4.0])
    assert len(slices) == 4
    assert slices[0].volume == pytest.approx(0.1)
    assert slices[-1].volume == pytest.approx(0.4)


def test_partial_fill_and_quality_metrics():
    broker = sim.MockBroker(_client_with_symbol())
    broker.set_partial_fill_ratio(0.5)

    router = sim.ExecutionRouter(broker)
    assert router.connect() is True
    router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0)

    routed = router.submit(_market_buy(1.0))
    assert routed.result.retcode == 10010

    summary = router.quality_summary()
    assert summary.samples >= 1
    assert summary.partial_fill_count >= 1
    assert summary.partial_fill_rate > 0.0
    assert summary.p99_latency_ms >= 0.0



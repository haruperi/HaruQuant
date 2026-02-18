"""Integration tests for C++ ExecutionRouter retry and escalation behavior."""

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


def _market_buy(volume: float = 0.1) -> "sim.TradeRequest":
    req = sim.TradeRequest()
    req.action = 1
    req.type = 0
    req.symbol = "EURUSD"
    req.volume = volume
    return req


def test_execution_router_risk_gate_blocks():
    broker = sim.MockBroker(_client_with_symbol())
    router = sim.ExecutionRouter(broker)
    assert router.connect() is True
    router.set_risk_account_state(7000.0, 10000.0, 0.1, 0.1)

    routed = router.submit(_market_buy())
    assert routed.risk_blocked is True
    assert routed.policy_code == "MAX_DRAWDOWN"
    assert routed.result.retcode == 10006


def test_execution_router_rate_limit_triggers():
    broker = sim.MockBroker(_client_with_symbol())
    policy = sim.ExecutionPolicy()
    policy.max_orders_per_window = 1
    policy.rate_limit_window_ms = 60000
    router = sim.ExecutionRouter(broker, policy)
    assert router.connect() is True
    router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0)

    first = router.submit(_market_buy())
    assert first.result.retcode == 10009

    second = router.submit(_market_buy())
    assert second.rate_limited is True
    assert second.policy_code == "RATE_LIMIT"
    assert second.result.retcode == 10024



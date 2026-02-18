from __future__ import annotations

import pandas as pd
import pytest

from apps.strategy import BaseStrategy, SignalRouter, StrategyAdapter


class AdapterTestStrategy(BaseStrategy):
    def on_init(self) -> None:
        self.state["ready"] = True

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        out = data.copy()
        out["entry_signal"] = 0
        out["exit_signal"] = 0
        out["price"] = out["close"]
        out.iloc[-1, out.columns.get_loc("entry_signal")] = 1
        return out

    def get_signal(self, data: pd.DataFrame, index: int):
        base = super().get_signal(data, index)
        if base is None:
            return None
        base["reason"] = "ema crossover"
        base["features"] = {"ema_fast": 1.1001, "ema_slow": 1.0998}
        base["confidence"] = 0.82
        base["tags"] = {"model": "rule_based"}
        base["metadata"] = {"source": "unit-test"}
        base["volume"] = 0.2
        base["order_type"] = "MARKET"
        base["time_in_force"] = "GTC"
        return base


def test_adapter_builds_canonical_signal_intent_and_event():
    strategy = AdapterTestStrategy({"symbol": "EURUSD", "strategy_id": "strat-1"})
    adapter = StrategyAdapter(strategy)
    df = pd.DataFrame(
        [{"close": 1.1010}, {"close": 1.1020}],
        index=[pd.Timestamp("2026-02-18T10:00:00Z"), pd.Timestamp("2026-02-18T10:01:00Z")],
    )
    out = adapter.on_bar(df)
    intent = adapter.build_signal_intent(out, len(out) - 1)
    assert intent is not None
    assert intent["action"] == "BUY"
    assert intent["qty"] == pytest.approx(0.2)
    assert intent["order_type"] == "MARKET"
    assert intent["time_in_force"] == "GTC"
    assert intent["strategy_id"] == "strat-1"
    assert intent["symbol"] == "EURUSD"
    assert intent["reason"] == "ema crossover"
    assert intent["features"]["ema_fast"] == pytest.approx(1.1001)
    assert intent["confidence"] == pytest.approx(0.82)
    assert intent["tags"]["model"] == "rule_based"
    assert intent["metadata"]["source"] == "unit-test"

    event = adapter.event_for_signal(intent, run_id="run-1", trace_id="trace-1", correlation_id="corr-1")
    assert event["payload"]["signal_intent"]["action"] == "BUY"
    assert event["strategy_id"] == "strat-1"
    assert event["symbol"] == "EURUSD"


def test_signal_router_routes_and_validates():
    routed = []
    router = SignalRouter(handler=lambda intent: routed.append(intent))
    intent = {
        "action": "SELL",
        "qty": 0.1,
        "order_type": "MARKET",
        "price": 1.1,
        "time_in_force": "DAY",
        "strategy_id": "s1",
        "symbol": "EURUSD",
    }
    router.route(intent)  # no exception
    assert len(routed) == 1

    bad = dict(intent)
    bad["order_type"] = "BAD"
    with pytest.raises(ValueError):
        router.route(bad)

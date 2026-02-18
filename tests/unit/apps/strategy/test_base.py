
import pytest
import pandas as pd
from apps.strategy.base import BaseStrategy, StrategyEvent

class ConcreteStrategy(BaseStrategy):
    def on_init(self) -> None:
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

@pytest.fixture
def strategy():
    return ConcreteStrategy({"symbol": "TEST"})

def test_init(strategy):
    assert strategy.symbol == "TEST"
    assert strategy.params["symbol"] == "TEST"
    assert strategy.strategy_id
    assert isinstance(strategy.state, dict)

def test_get_signal_none(strategy):
    data = pd.DataFrame([{"entry_signal": 0, "exit_signal": 0}])
    assert strategy.get_signal(data, 0) is None

def test_get_signal_entry(strategy):
    # entry_signal=1, price=100
    df = pd.DataFrame([
        {"entry_signal": 1, "price": 100.0, "exit_signal": 0}
    ], index=[pd.Timestamp("2023-01-01")])
    
    signal = strategy.get_signal(df, 0)
    assert signal is not None
    assert signal["entry_signal"] == 1
    assert signal["price"] == 100.0
    assert signal["time"] == pd.Timestamp("2023-01-01")

def test_crossover(strategy):
    # s1 crosses above s2
    # T0: s1=10, s2=10
    # T1: s1=12, s2=11 -> Crossover
    s1 = pd.Series([10, 12])
    s2 = pd.Series([10, 11])
    assert strategy.crossover(s1, s2) is True
    
    # No crossover
    s1 = pd.Series([10, 9])
    s2 = pd.Series([10, 10])
    assert strategy.crossover(s1, s2) is False

def test_crossunder(strategy):
    # s1 crosses below s2
    # T0: s1=10, s2=10
    # T1: s1=9, s2=11 -> Crossunder
    s1 = pd.Series([10, 9])
    s2 = pd.Series([10, 11])
    assert strategy.crossunder(s1, s2) is True


def test_lifecycle_optional_hooks_default_noop(strategy):
    event: StrategyEvent = {
        "event_id": "evt-1",
        "event_type": "trade",
        "symbol": "TEST",
        "strategy_id": strategy.strategy_id,
        "event_ts": pd.Timestamp("2026-01-01T00:00:00Z"),
        "recv_ts": pd.Timestamp("2026-01-01T00:00:00Z"),
        "payload": {"ticket": 1},
        "run_id": "run-1",
        "trace_id": "trace-1",
        "correlation_id": "corr-1",
    }
    assert strategy.on_trade(event) is None
    assert strategy.on_order_update(event) is None
    assert strategy.on_timer(event) is None
    assert strategy.on_shutdown(event) is None


def test_strategy_state_isolation_between_instances():
    a = ConcreteStrategy({"symbol": "AAA"})
    b = ConcreteStrategy({"symbol": "BBB"})

    a.state["counter"] = 1
    assert "counter" not in b.state

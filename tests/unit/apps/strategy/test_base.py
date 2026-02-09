
import pytest
import pandas as pd
import numpy as np
from apps.strategy.base import BaseStrategy

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

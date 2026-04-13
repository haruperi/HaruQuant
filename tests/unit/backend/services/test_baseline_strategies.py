from __future__ import annotations

import pandas as pd

from backend.services.strategy.adapter import StrategyAdapter
from backend.services.strategy.baselines import (
    EmaCrossBaselineStrategy,
    NaiveMomentumStrategy,
    RsiBaselineStrategy,
)


def _bars(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value + 0.5 for value in closes],
            "low": [value - 0.5 for value in closes],
            "close": closes,
            "volume": [1000] * len(closes),
        },
        index=index,
    )


def test_rsi_baseline_generates_sell_signal_for_overbought_series() -> None:
    strategy = RsiBaselineStrategy(
        {
            "symbol": "EURUSD",
            "period": 3,
            "oversold": 30,
            "overbought": 70,
        }
    )

    result = strategy.on_bar(_bars([1, 2, 3, 4, 5, 6]))
    signal = strategy.get_signal(result, len(result) - 1)

    assert signal is not None
    assert signal["entry_signal"] == -1
    assert signal["price"] == 6.0
    assert "overbought" in str(signal["reason"])


def test_rsi_baseline_generates_buy_signal_for_oversold_series() -> None:
    strategy = RsiBaselineStrategy(
        {
            "symbol": "EURUSD",
            "period": 3,
            "oversold": 30,
            "overbought": 70,
        }
    )

    result = strategy.on_bar(_bars([6, 5, 4, 3, 2, 1]))
    signal = strategy.get_signal(result, len(result) - 1)

    assert signal is not None
    assert signal["entry_signal"] == 1
    assert signal["price"] == 1.0
    assert "oversold" in str(signal["reason"])


def test_ema_cross_baseline_generates_canonical_signal_intent() -> None:
    strategy = EmaCrossBaselineStrategy(
        {
            "symbol": "EURUSD",
            "fast_period": 2,
            "slow_period": 3,
            "strategy_id": "ema-cross-test",
        }
    )
    result = strategy.on_bar(_bars([5, 4, 3, 2, 3, 4, 5, 6]))
    signal_indexes = [
        index
        for index in range(len(result))
        if strategy.get_signal(result, index) is not None
    ]

    assert signal_indexes
    adapter = StrategyAdapter(strategy, default_qty=0.5)
    intent = adapter.build_signal_intent(
        result,
        signal_indexes[-1],
        tags=["baseline", "ema_cross"],
        metadata={"source": "unit-test"},
    )

    assert intent is not None
    assert intent["action"] in {"BUY", "SELL"}
    assert intent["qty"] == 0.5
    assert intent["symbol"] == "EURUSD"
    assert intent["strategy_id"] == "ema-cross-test"
    assert intent["metadata"] == {"source": "unit-test"}
    assert "ema_cross" in intent["tags"]


def test_naive_momentum_generates_buy_and_sell_signals() -> None:
    strategy = NaiveMomentumStrategy(
        {
            "symbol": "EURUSD",
            "lookback": 2,
            "threshold": 0.05,
        }
    )

    up_result = strategy.on_bar(_bars([1.0, 1.0, 1.2]))
    down_result = strategy.on_bar(_bars([1.2, 1.2, 1.0]))

    up_signal = strategy.get_signal(up_result, len(up_result) - 1)
    down_signal = strategy.get_signal(down_result, len(down_result) - 1)

    assert up_signal is not None
    assert up_signal["entry_signal"] == 1
    assert down_signal is not None
    assert down_signal["entry_signal"] == -1


def test_baseline_strategy_rejects_invalid_parameters() -> None:
    strategy = EmaCrossBaselineStrategy(
        {
            "symbol": "EURUSD",
            "fast_period": 5,
            "slow_period": 3,
        }
    )

    try:
        strategy.on_bar(_bars([1, 2, 3, 4, 5]))
    except ValueError as exc:
        assert "fast_period" in str(exc)
    else:
        raise AssertionError("invalid EMA parameters should fail")

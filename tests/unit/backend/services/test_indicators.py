from __future__ import annotations

import pandas as pd
import pytest

from services.indicator import (
    accumulation_distribution,
    atr,
    bbands,
    ema,
    require_columns,
    require_dataframe,
    require_positive_int,
    rsi,
    sma,
    wma,
)


def _ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [1.0, 1.1, 1.2, 1.15, 1.18],
            "high": [1.2, 1.25, 1.3, 1.22, 1.24],
            "low": [0.95, 1.05, 1.1, 1.1, 1.15],
            "close": [1.1, 1.2, 1.15, 1.18, 1.22],
            "volume": [100, 120, 130, 110, 140],
        }
    )


def test_indicator_functions_add_expected_columns_without_mutating_input() -> None:
    data = _ohlcv()

    outputs = [
        sma(data, window=3),
        ema(data, span=3),
        wma(data, window=3),
        rsi(data, period=3),
        atr(data, period=3),
        bbands(data, period=3, std_dev=2.0),
        accumulation_distribution(data),
    ]

    assert "sma_3" in outputs[0]
    assert "ema_3" in outputs[1]
    assert "wma_3" in outputs[2]
    assert "rsi_3" in outputs[3]
    assert "atr_3" in outputs[4]
    assert {"bb_upper_3_2", "bb_middle_3_2", "bb_lower_3_2"}.issubset(outputs[5].columns)
    assert "adl" in outputs[6]
    assert list(data.columns) == ["open", "high", "low", "close", "volume"]


def test_indicator_validation_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        require_dataframe(pd.DataFrame())

    with pytest.raises(ValueError, match="Missing required columns"):
        require_columns(pd.DataFrame({"close": [1.0]}), ("open", "close"))

    with pytest.raises(ValueError, match="window must be positive"):
        require_positive_int(0, name="window")

    with pytest.raises(ValueError, match="Missing required columns"):
        atr(pd.DataFrame({"close": [1.0]}), period=3)

import numpy as np
import pandas as pd

from backend.services.simulation.vectorized import (
    prepare_vectorized_data,
    reconstruct_equity_curve,
    reconstruct_trades,
)


def _ticks():
    return pd.DataFrame(
        {
            "bid": [1.1000, 1.1010, 1.1020],
            "ask": [1.1002, 1.1012, 1.1022],
            "symbol": ["AUDUSD", "AUDUSD", "AUDUSD"],
            "is_bar_close": [False, False, True],
            "entry_signal": [1, 0, 0],
            "exit_signal": [0, 0, 1],
            "sl": [1.0900, 0.0, 0.0],
            "tp": [1.1200, 0.0, 0.0],
        },
        index=pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
                "2025-01-01 01:00:00",
            ]
        ),
    )


def test_prepare_vectorized_data_maps_columns_and_events():
    prepared = prepare_vectorized_data(_ticks())

    assert prepared["bid_arr"].tolist() == [1.1000, 1.1010, 1.1020]
    assert prepared["ask_arr"].tolist() == [1.1002, 1.1012, 1.1022]
    assert prepared["id_to_symbol"] == {0: "AUDUSD"}
    assert prepared["symbol_id_arr"].tolist() == [0, 0, 0]
    assert prepared["event_indices"].tolist() == [0, 2]
    assert prepared["entry_signals"].tolist() == [1.0, 0.0, 0.0]
    assert prepared["exit_signals"].tolist() == [0.0, 0.0, 1.0]


def test_reconstruct_trades_and_equity_curve_from_arrays():
    prepared = prepare_vectorized_data(_ticks())
    trades_arr = np.array(
        [
            [
                1.0,
                0.0,
                0.0,
                1.1002,
                1.1020,
                0.01,
                1.0900,
                1.1200,
                0.0,
                2.0,
                1.8,
                3.0,
            ]
        ]
    )
    equity_arr = np.array([[2.0, 10001.8]])

    trades = reconstruct_trades(trades_arr, prepared, contract_size=100000.0)
    equity = reconstruct_equity_curve(equity_arr, prepared)

    assert len(trades) == 1
    assert trades[0].ticket == 1
    assert trades[0].symbol == "AUDUSD"
    assert trades[0].type == "buy"
    assert trades[0].profit_loss == 1.8
    assert trades[0].exit_reason == "signal"
    assert len(equity) == 1
    assert equity[0].equity == 10001.8

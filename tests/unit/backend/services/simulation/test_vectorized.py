import numpy as np
import pandas as pd

from backend.services.simulation.vectorized import (
    prepare_vectorized_data,
    reconstruct_equity_curve,
    reconstruct_trades,
    run_vectorized_simulation,
)


def _ticks():
    return pd.DataFrame(
        {
            "bid": [1.1000, 1.1010, 1.1020],
            "ask": [1.1002, 1.1012, 1.1022],
            "symbol": ["AUDUSD", "AUDUSD", "AUDUSD"],
            "is_bar_close": ["open", "high", "close"],
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
    assert prepared["event_indices"].tolist() == [0, 1, 2]
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
                -1.4,
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
    assert trades[0].commission == -1.4
    assert trades[0].exit_reason == "signal"
    assert len(equity) == 1
    assert equity[0].equity == 10001.8


def test_run_vectorized_simulation_uses_configured_position_size(monkeypatch):
    import backend.services.simulation.vectorized as vectorized

    captured = {}

    def fake_kernel(
        bid_arr,
        ask_arr,
        symbol_id_arr,
        is_bar_close_arr,
        event_indices,
        entry_signals,
        exit_signals,
        sl_arr,
        tp_arr,
        initial_balance,
        contract_size,
        position_size,
        commission_per_lot,
        slippage_points,
        point_value,
        num_symbols,
        snapshot_requires_open_positions,
    ):
        captured["position_size"] = position_size
        captured["commission_per_lot"] = commission_per_lot
        captured["slippage_points"] = slippage_points.tolist()
        captured["point_value"] = point_value
        captured["num_symbols"] = num_symbols
        captured["snapshot_requires_open_positions"] = snapshot_requires_open_positions
        return np.empty((0, 13)), np.empty((0, 2)), initial_balance

    class FakeEngine:
        def __init__(self):
            account = type("Account", (), {"balance": 0.0, "equity": 0.0})()
            self.state = type(
                "State",
                (),
                {
                    "completed_trade_records": [],
                    "completed_equity_curve": [],
                    "trading_account": account,
                },
            )()

    monkeypatch.setattr(vectorized, "njit", object())
    monkeypatch.setattr(vectorized, "_run_turbo_sim_numba", fake_kernel)

    processed = run_vectorized_simulation(
        FakeEngine(),
        _ticks(),
        initial_balance=10000.0,
        contract_size=100000.0,
        position_size=0.25,
        commission_per_lot=7.0,
        slippage_model="fixed",
        slippage_points=2.0,
    )

    assert processed == 3
    assert captured["position_size"] == 0.25
    assert captured["commission_per_lot"] == 7.0
    assert captured["slippage_points"] == [2.0, 2.0, 2.0]
    assert captured["point_value"] == 0.00001
    assert captured["num_symbols"] == 1
    assert captured["snapshot_requires_open_positions"] is False


def test_run_vectorized_simulation_uses_dynamic_slippage_bounds(monkeypatch):
    import backend.services.simulation.vectorized as vectorized

    captured = {}

    def fake_kernel(
        bid_arr,
        ask_arr,
        symbol_id_arr,
        is_bar_close_arr,
        event_indices,
        entry_signals,
        exit_signals,
        sl_arr,
        tp_arr,
        initial_balance,
        contract_size,
        position_size,
        commission_per_lot,
        slippage_points,
        point_value,
        num_symbols,
        snapshot_requires_open_positions,
    ):
        captured["slippage_points"] = slippage_points.tolist()
        return np.empty((0, 13)), np.empty((0, 2)), initial_balance

    class FakeEngine:
        def __init__(self):
            account = type("Account", (), {"balance": 0.0, "equity": 0.0})()
            self.state = type(
                "State",
                (),
                {
                    "completed_trade_records": [],
                    "completed_equity_curve": [],
                    "trading_account": account,
                },
            )()

    monkeypatch.setattr(vectorized, "njit", object())
    monkeypatch.setattr(vectorized, "_run_turbo_sim_numba", fake_kernel)

    run_vectorized_simulation(
        FakeEngine(),
        _ticks(),
        slippage_model="dynamic",
        slippage_min=1.0,
        slippage_max=3.0,
    )

    assert len(captured["slippage_points"]) == 3
    assert min(captured["slippage_points"]) >= 1.0
    assert max(captured["slippage_points"]) <= 3.0


def test_prepare_vectorized_data_bar_close_policy_uses_close_ticks_only():
    prepared = prepare_vectorized_data(_ticks(), snapshot_policy="bar_close")

    assert prepared["event_indices"].tolist() == [0, 2]


def test_run_vectorized_simulation_corrects_profit_with_engine(monkeypatch):
    import backend.services.simulation.vectorized as vectorized

    def fake_kernel(
        *args,
        **kwargs,
    ):
        # Return one completed trade at tick index 2
        trades = np.array(
            [
                [
                    1.0,  # ticket
                    0.0,  # symbol_id
                    0.0,  # type (buy)
                    1.1002,  # open_price
                    1.1020,  # close_price
                    0.01,  # volume
                    0.0,  # sl
                    0.0,  # tp
                    0.0,  # open_idx
                    2.0,  # close_idx
                    1.8,  # profit (simple calc: (1.1020-1.1002)*0.01*100000 = 1.8)
                    3.0,  # reason
                    0.0,  # commission
                ]
            ]
        )
        # Equity curve point at tick index 2
        equity = np.array([[2.0, 10001.8]])
        return trades, equity, 10001.8

    class FakeEngine:
        def __init__(self):
            account = type("Account", (), {"balance": 0.0, "equity": 0.0})()
            self.state = type(
                "State",
                (),
                {
                    "completed_trade_records": [],
                    "completed_equity_curve": [],
                    "trading_account": account,
                },
            )()

        def _strict_order_calc_profit(self, type, symbol, volume, open, close):
            # Return a different profit to test correction
            return 2.5

    monkeypatch.setattr(vectorized, "njit", object())
    monkeypatch.setattr(vectorized, "_run_turbo_sim_numba", fake_kernel)

    engine = FakeEngine()
    run_vectorized_simulation(
        engine,
        _ticks(),
        initial_balance=10000.0,
    )

    # Corrected profit should be 2.5 instead of 1.8
    assert engine.state.completed_trade_records[0].profit_loss == 2.5
    # Balance delta is 2.5 - 1.8 = 0.7. Final balance should be 10001.8 + 0.7 = 10002.5
    assert engine.state.trading_account.balance == 10002.5
    # Equity curve should also be corrected
    assert engine.state.completed_equity_curve[0].equity == 10002.5

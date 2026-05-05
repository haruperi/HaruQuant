from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from haruquant.simulation import data_preparation as data_preparation
from haruquant.simulation import SimulationConfig
from haruquant.simulation import (
    SimulationDataPreparationError,
    SimulationDataPreparer,
)
from haruquant.simulation import register_strategy
from haruquant.strategy import BaseStrategy
from haruquant.data import TicksGenerator


class FixtureSignalStrategy(BaseStrategy):
    def on_init(self) -> None:
        return None

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        out = data.copy()
        out["entry_signal"] = 0
        out["exit_signal"] = 0
        out["pending_signal"] = 0
        out["cancel_pending_signal"] = 0
        out["price"] = 0.0
        out["sl"] = 0.0
        out["tp"] = 0.0
        out.iloc[1, out.columns.get_loc("entry_signal")] = 1
        return out

    def get_signal(self, data: pd.DataFrame, index: int):
        return None


class FakeClient:
    def __init__(self, bars_by_key, ticks_by_symbol=None):
        self.bars_by_key = bars_by_key
        self.ticks_by_symbol = ticks_by_symbol or {}
        self.get_bars_calls = []
        self.get_ticks_calls = []

    def get_bars(self, symbol, timeframe, date_from, date_to):
        self.get_bars_calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        value = self.bars_by_key.get((symbol, timeframe))
        return None if value is None else value.copy()

    def get_ticks(self, symbol, start, end):
        self.get_ticks_calls.append(
            {
                "symbol": symbol,
                "start": start,
                "end": end,
            }
        )
        value = self.ticks_by_symbol.get(symbol)
        return None if value is None else value.copy()

    def symbol_info(self, symbol):
        return SimpleNamespace(point=0.00001)


class FakeEngine:
    def __init__(self, client):
        self.client = client


def _bars(start="2024-12-31", periods=30, freq="h"):
    index = pd.date_range(start=start, periods=periods, freq=freq)
    base = [1.0 + (i * 0.01) for i in range(periods)]
    return pd.DataFrame(
        {
            "open": base,
            "high": [value + 0.02 for value in base],
            "low": [value - 0.01 for value in base],
            "close": [value + 0.01 for value in base],
            "spread": [10 for _ in range(periods)],
        },
        index=index,
    )


def _ticks():
    index = pd.to_datetime(
        [
            "2025-01-01 00:00:00",
            "2025-01-01 00:30:00",
            "2025-01-01 01:00:00",
            "2025-01-01 01:30:00",
        ]
    )
    return pd.DataFrame(
        {
            "bid": [1.1000, 1.1001, 1.1010, 1.1012],
            "ask": [1.1002, 1.1003, 1.1012, 1.1014],
        },
        index=index,
    )


def _config(
    symbols=None,
    tick_model="timeframe_ticks",
    extra_execution=None,
    data_source="metatrader",
    local_files=None,
):
    execution = {
        "tick_model": tick_model,
        "spread_model": "native_spread",
        "contract_size": 100000,
        "position_size": {"type": "fixed_lot", "lot_size": 0.1},
    }
    if extra_execution:
        execution.update(extra_execution)
    return SimulationConfig.from_dict(
        {
            "engine_type": "vectorized",
            "account": {"initial_balance": 10000},
            "data": {
                "source": data_source,
                "symbols": symbols or ["AUDUSD"],
                "timeframe": "H1",
                "start": "2025-01-01",
                "end": "2025-01-02",
                "warmup_start": "2024-12-31",
                **({"local_files": local_files} if local_files is not None else {}),
            },
            "strategy": {"name": "FixtureSignalStrategy", "params": {"fast": 1}},
            "execution": execution,
        }
    )


def setup_module():
    register_strategy("FixtureSignalStrategy", FixtureSignalStrategy)


def test_prepare_symbol_builds_timeframe_ticks_and_metadata():
    client = FakeClient({("AUDUSD", "H1"): _bars()})
    prepared = SimulationDataPreparer(FakeEngine(client)).prepare_symbol(
        _config(),
        "AUDUSD",
    )

    assert len(prepared.ticks) == 24
    assert prepared.tick_counts_by_symbol["AUDUSD"] == 24
    assert prepared.signal_bars_by_symbol["AUDUSD"].index.min() >= datetime(2025, 1, 1)
    assert set(["bid", "ask", "entry_signal", "exit_signal", "is_bar_close", "symbol"]).issubset(
        prepared.ticks.columns
    )
    assert set(prepared.ticks["is_bar_close"].unique()) == {"open", "high", "low", "close"}
    assert prepared.ticks["symbol"].eq("AUDUSD").all()
    assert prepared.ticks["signal_timeframe"].eq("H1").all()
    assert prepared.metadata["point_value"] == 0.00001


def test_timeframe_ticks_place_close_at_end_of_bar():
    bars = _bars(start="2025-01-01", periods=1, freq="h")
    ticks = TicksGenerator(
        model="timeframe_ticks",
        trading_timeframe="H1",
        point_value=0.00001,
        spread_model="native_spread",
    ).generate(bars)

    assert list(ticks.index) == [
        pd.Timestamp("2025-01-01 00:00:00"),
        pd.Timestamp("2025-01-01 00:20:00"),
        pd.Timestamp("2025-01-01 00:40:00"),
        pd.Timestamp("2025-01-01 00:59:59.999000"),
    ]


def test_prepare_merges_multiple_symbols_in_datetime_order():
    client = FakeClient(
        {
            ("AUDUSD", "H1"): _bars(),
            ("EURGBP", "H1"): _bars(),
        }
    )
    prepared = SimulationDataPreparer(FakeEngine(client)).prepare(
        _config(symbols=["AUDUSD", "EURGBP"])
    )

    assert len(prepared.ticks) == 48
    assert prepared.tick_counts_by_symbol == {"AUDUSD": 24, "EURGBP": 24}
    assert prepared.metadata["tick_count"] == 48
    assert prepared.ticks.index.is_monotonic_increasing
    assert set(prepared.ticks["symbol"].unique()) == {"AUDUSD", "EURGBP"}


def test_prepare_loads_m1_data_for_m1_ticks():
    client = FakeClient(
        {
            ("AUDUSD", "H1"): _bars(),
            ("AUDUSD", "M1"): _bars(start="2025-01-01", periods=4, freq="min"),
        }
    )
    prepared = SimulationDataPreparer(FakeEngine(client)).prepare_symbol(
        _config(tick_model="m1_ticks"),
        "AUDUSD",
    )

    assert len(prepared.ticks) == 16
    assert any(call["timeframe"] == "M1" for call in client.get_bars_calls)


def test_prepare_loads_metatrader_real_ticks():
    client = FakeClient(
        {("AUDUSD", "H1"): _bars()},
        ticks_by_symbol={"AUDUSD": _ticks()},
    )
    prepared = SimulationDataPreparer(FakeEngine(client)).prepare_symbol(
        _config(tick_model="real_ticks"),
        "AUDUSD",
    )

    assert len(prepared.ticks) == 4
    assert prepared.ticks["bid"].tolist() == [1.1000, 1.1001, 1.1010, 1.1012]
    assert prepared.ticks["symbol"].eq("AUDUSD").all()
    assert client.get_ticks_calls[0]["symbol"] == "AUDUSD"


def test_prepare_loads_local_csv_bars(tmp_path):
    csv_path = tmp_path / "audusd_h1.csv"
    _bars().reset_index(names="timestamp").to_csv(csv_path, index=False)

    prepared = SimulationDataPreparer(FakeEngine(client=None)).prepare_symbol(
        _config(
            data_source="local",
            local_files={"AUDUSD": {"bars": str(csv_path)}},
        ),
        "AUDUSD",
    )

    assert len(prepared.ticks) == 24
    assert prepared.ticks["symbol"].eq("AUDUSD").all()


def test_prepare_loads_local_csv_real_ticks(tmp_path):
    bars_path = tmp_path / "audusd_h1.csv"
    ticks_path = tmp_path / "audusd_ticks.csv"
    _bars().reset_index(names="timestamp").to_csv(bars_path, index=False)
    _ticks().reset_index(names="timestamp").to_csv(ticks_path, index=False)

    prepared = SimulationDataPreparer(FakeEngine(client=None)).prepare_symbol(
        _config(
            tick_model="real_ticks",
            data_source="local",
            local_files={
                "AUDUSD": {
                    "bars": str(bars_path),
                    "ticks": str(ticks_path),
                }
            },
        ),
        "AUDUSD",
    )

    assert len(prepared.ticks) == 4
    assert set(["bid", "ask", "source_bar_time"]).issubset(prepared.ticks.columns)


def test_prepare_loads_dukascopy_real_ticks(monkeypatch):
    calls = []

    def fake_fetch(instrument, interval, offer_side, start, end):
        calls.append(
            {
                "instrument": instrument,
                "interval": interval,
                "offer_side": offer_side,
                "start": start,
                "end": end,
            }
        )
        index = pd.to_datetime(
            ["2025-01-01 00:00:00", "2025-01-01 00:30:00"],
            utc=True,
        )
        return pd.DataFrame(
            {
                "bidprice": [1.1000, 1.1001],
                "askprice": [1.1002, 1.1003],
                "bidvolume": [1.0, 2.0],
                "askvolume": [1.0, 2.0],
            },
            index=index,
        )

    monkeypatch.setattr(data_preparation, "fetch", fake_fetch)
    monkeypatch.setattr(
        data_preparation,
        "load_dukascopy",
        lambda **_: _bars(),
    )

    prepared = SimulationDataPreparer(FakeEngine(client=None)).prepare_symbol(
        _config(tick_model="real_ticks", data_source="dukascopy"),
        "AUDUSD",
    )

    assert len(prepared.ticks) == 2
    assert calls[0]["instrument"] == "AUD/USD"
    assert calls[0]["interval"] == data_preparation.INTERVAL_TICK
    assert prepared.ticks["bid"].tolist() == [1.1000, 1.1001]


def test_prepare_raises_when_bars_missing():
    client = FakeClient({})

    with pytest.raises(SimulationDataPreparationError, match="no bars"):
        SimulationDataPreparer(FakeEngine(client)).prepare_symbol(_config(), "AUDUSD")


def test_prepare_raises_when_real_ticks_missing():
    client = FakeClient({("AUDUSD", "H1"): _bars()})

    with pytest.raises(SimulationDataPreparationError, match="no real ticks"):
        SimulationDataPreparer(FakeEngine(client)).prepare_symbol(
            _config(tick_model="real_ticks"),
            "AUDUSD",
        )

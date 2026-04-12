from __future__ import annotations

import pytest
from types import SimpleNamespace

import pandas as pd

from backend.services.risk_engine import (
    HypotheticalOrderAction,
    ReplayClock,
    ReplayEngine,
    RiskLimits,
    TimelineReconstructor,
    WhatIfEngine,
)


def _bars(periods: int = 6, start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.0004) + ((base % 3) * 0.0001)
    return pd.DataFrame(
        {
            "Open": close - 0.0002,
            "High": close + 0.0005,
            "Low": close - 0.0005,
            "Close": close,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 + (i % 2) for i in range(periods)],
        },
        index=idx,
    )


def _ticks() -> pd.DataFrame:
    index = pd.to_datetime(
        [
            "2024-01-01 00:00:00",
            "2024-01-01 00:15:00",
            "2024-01-01 01:00:00",
            "2024-01-01 01:15:00",
        ]
    )
    return pd.DataFrame(
        {
            "bid": [1.1000, 1.1005, 1.1010, 1.1014],
            "ask": [1.1002, 1.1007, 1.1012, 1.1016],
            "source_bar_time": pd.to_datetime(
                [
                    "2024-01-01 00:00:00",
                    "2024-01-01 00:00:00",
                    "2024-01-01 01:00:00",
                    "2024-01-01 01:00:00",
                ]
            ),
        },
        index=index,
    )


class FakeReplayEngine:
    def __init__(self):
        self.state = SimpleNamespace(current_tick_datetime=None, current_tick_epoch=None)
        self._account = {
            "equity": 10000.0,
            "balance": 10000.0,
            "margin": 500.0,
            "margin_free": 9500.0,
            "currency": "USD",
        }
        self._positions = [
            SimpleNamespace(symbol="EURUSD", volume=0.10, type="BUY", price_open=1.1000),
        ]
        self._symbols = {
            "EURUSD": SimpleNamespace(
                name="EURUSD",
                trade_contract_size=100000.0,
                trade_tick_value=10.0,
                trade_tick_size=0.0001,
                volume_min=0.01,
                volume_step=0.01,
                bid=1.1000,
                ask=1.1002,
                point=0.0001,
            )
        }
        self._equity_curve = []
        self.run_schedule = {
            "positions": None,
            "pending_orders": None,
            "account": None,
            "portfolio": None,
            "risk": None,
        }

    def configure_run_schedule(self, positions_every=None, pending_orders_every=None, account_every=None, portfolio_every=None, risk_every=None):
        self.run_schedule["positions"] = positions_every
        self.run_schedule["pending_orders"] = pending_orders_every
        self.run_schedule["account"] = account_every
        self.run_schedule["portfolio"] = portfolio_every
        self.run_schedule["risk"] = risk_every

    def account_info(self):
        return self._account

    def positions_get(self):
        return tuple(self._positions)

    def symbol_info(self, symbol: str):
        return self._symbols.get(symbol)

    def monitor_positions(self, verbose: bool = False):
        _ = verbose
        return None

    def monitor_pending_orders(self, verbose: bool = False):
        _ = verbose
        return None

    def monitor_account(self, verbose: bool = False):
        _ = verbose
        timestamp = self.state.current_tick_datetime
        if timestamp is None:
            return None
        if self._equity_curve and pd.Timestamp(self._equity_curve[-1].timestamp) == pd.Timestamp(timestamp):
            return None
        self._equity_curve.append(
            SimpleNamespace(
                timestamp=pd.Timestamp(timestamp),
                equity=float(self._account["equity"]),
                balance=float(self._account["balance"]),
                drawdown=0.0,
                exposure=0.0,
            )
        )
        return None

    def get_equity_curve(self):
        return list(self._equity_curve)

    def run(self, data, frame_observer=None, **kwargs):
        _ = kwargs
        for idx, (timestamp, row) in enumerate(data.iterrows(), start=1):
            self.state.current_tick_datetime = pd.Timestamp(timestamp)
            self.state.current_tick_epoch = int(pd.Timestamp(timestamp).timestamp())
            self._account["equity"] = 10000.0 + (idx * 10.0)
            self._account["margin_free"] = self._account["equity"] - self._account["margin"]
            self._symbols["EURUSD"].bid = float(row["bid"])
            self._symbols["EURUSD"].ask = float(row["ask"])
            if frame_observer is not None:
                frame_observer(engine=self, timestamp=timestamp, tick_number=idx, batch_end=idx)
        return len(data)


def test_timeline_reconstructor_builds_bar_capture_points():
    timeline = TimelineReconstructor().build_timeline(_ticks(), frame_mode="bar")

    assert len(timeline) == 2
    assert timeline[0].frame_timestamp == pd.Timestamp("2024-01-01 00:00:00")
    assert timeline[0].capture_timestamp == pd.Timestamp("2024-01-01 00:15:00")
    assert timeline[1].frame_timestamp == pd.Timestamp("2024-01-01 01:00:00")


def test_replay_engine_builds_replay_frames():
    fake_engine = FakeReplayEngine()
    replay = ReplayEngine().replay(
        engine=fake_engine,
        data=_ticks(),
        symbols=["EURUSD"],
        timeframe="H1",
        market_data={"EURUSD": _bars()},
        limits=RiskLimits(vol_lookback=2, corr_lookback=2),
        symbol_to_cluster={"EURUSD": "FOREX"},
        frame_mode="bar",
        include_recommendations=False,
    )

    assert replay.summary["frame_count"] == 2
    assert len(replay.frames) == 2
    assert replay.frames[0].state.positions
    assert replay.frames[0].cockpit_state is not None
    assert replay.frames[0].cockpit_state.account["equity"] > 0

    clock = ReplayClock.from_timeline(replay.timeline)
    assert clock.current is not None
    assert clock.advance() is not None
    assert clock.advance() is not None
    assert clock.finished is True


def test_what_if_engine_projects_hypothetical_state_without_mutating_baseline():
    fake_engine = FakeReplayEngine()
    replay = ReplayEngine().replay(
        engine=fake_engine,
        data=_ticks(),
        symbols=["EURUSD"],
        timeframe="H1",
        market_data={"EURUSD": _bars()},
        limits=RiskLimits(vol_lookback=2, corr_lookback=2),
        symbol_to_cluster={"EURUSD": "FOREX"},
        frame_mode="bar",
        include_recommendations=False,
    )
    baseline = replay.frames[-1]

    comparison = WhatIfEngine().evaluate(
        baseline,
        actions=[HypotheticalOrderAction(action_type="add", symbol="EURUSD", delta_lots=0.05)],
        include_recommendations=False,
    )

    assert baseline.state.position_map["EURUSD"] == 0.10
    assert comparison.projected_state.position_map["EURUSD"] == pytest.approx(0.15)
    assert "overall_score_delta" in comparison.summary

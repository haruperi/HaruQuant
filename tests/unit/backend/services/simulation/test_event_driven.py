from types import SimpleNamespace

import pandas as pd

from haruquant.simulation import engine as engine_module
from haruquant.simulation import Engine
from haruquant.simulation import run_event_driven_simulation


class FastPathEngine:
    def __init__(self):
        self.run_schedule = {
            "auto": None,
            "positions": None,
            "pending_orders": None,
            "account": None,
            "portfolio": None,
            "risk": None,
        }
        self.state = SimpleNamespace(
            current_tick_datetime=None,
            current_tick_epoch=None,
            execution_settings={},
        )
        self.account = {}

    def account_info(self):
        return self.account

    def _risk_enabled(self):
        return False


class SnapshotPolicyEngine:
    def __init__(self, policy: str):
        self.run_schedule = {
            "auto": True,
            "positions": None,
            "pending_orders": None,
            "account": None,
            "portfolio": None,
            "risk": None,
        }
        self.state = SimpleNamespace(
            current_tick_datetime=None,
            current_tick_epoch=None,
            execution_settings={},
        )
        self.account = {}
        self.equity_snapshot_policy = policy
        self._schedule_state_dirty = False
        self.default_signal_volume = 0.01
        self.monitor_account_calls = 0
        self.monitor_positions_calls = 0

    def account_info(self):
        return self.account

    def _risk_enabled(self):
        return False

    def _build_symbol_map(self):
        return {}

    def _default_run_symbol(self):
        return "AUDUSD"

    def _resolve_tick_symbol(self, batch_idx, symbol_values, default_symbol):
        return default_symbol

    def _update_symbol_tick(self, symbol_map, symbol_name, bid, ask):
        return None

    def _apply_tick_signals(self, **kwargs):
        return False

    def _has_open_positions(self):
        return True

    def _has_pending_orders(self):
        return False

    def monitor_positions(self, verbose=False):
        self.monitor_positions_calls += 1

    def monitor_account(self, verbose=False):
        self.monitor_account_calls += 1

    def monitor_portfolio(self, verbose=False):
        return None

    def monitor_risk(self, verbose=False):
        return None

    def _run_scheduled_callbacks(self, tick_number: int, verbose: bool = False, is_bar_close: bool = False):
        if self.run_schedule.get("auto") and is_bar_close:
            if self.equity_snapshot_policy == "bar_close" and self._has_open_positions():
                self.monitor_positions(verbose=verbose)
            if self.equity_snapshot_policy == "bar_close":
                self.monitor_account(verbose=verbose)
            self._schedule_state_dirty = False


def _ticks_with_bar_close():
    return pd.DataFrame(
        {
            "bid": [1.1000, 1.1003, 1.0998, 1.1002],
            "ask": [1.1002, 1.1005, 1.1000, 1.1004],
            "is_bar_close": ["open", "high", "low", "close"],
        },
        index=pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:01",
                "2025-01-01 00:00:02",
                "2025-01-01 00:00:03",
            ]
        ),
    )


def _ticks():
    return pd.DataFrame(
        {
            "bid": [1.1000, 1.1001, 1.1002],
            "ask": [1.1002, 1.1003, 1.1004],
        },
        index=pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:01",
                "2025-01-01 00:00:02",
            ]
        ),
    )


def test_event_driven_fast_path_counts_ticks_without_signals():
    engine = FastPathEngine()

    processed = run_event_driven_simulation(
        engine,
        _ticks(),
        commission_per_lot=7.0,
        slippage_model="fixed",
        slippage_points=2.0,
        slippage_min=1.0,
        slippage_max=5.0,
    )

    assert processed == 3
    assert engine.account["commission"] == 7.0
    assert engine.state.execution_settings == {
        "slippage_model": "fixed",
        "slippage_points": 2.0,
        "slippage_min": 1.0,
        "slippage_max": 5.0,
    }


def test_engine_run_event_driven_delegates_to_module(monkeypatch):
    calls = []

    def fake_run_event_driven_simulation(engine, data, **kwargs):
        calls.append((engine, data, kwargs))
        return 5

    monkeypatch.setattr(
        engine_module,
        "run_event_driven_simulation",
        fake_run_event_driven_simulation,
    )
    engine = Engine.__new__(Engine)
    ticks = _ticks()

    processed = engine.run_event_driven(
        ticks,
        position_size=0.2,
        commission_per_lot=7.0,
        slippage_model="fixed",
        slippage_points=1.0,
        slippage_min=0.5,
        slippage_max=4.0,
        monitor_verbose=True,
        show_progress=False,
        progress_desc="Check",
        frame_observer="observer",
    )

    assert processed == 5
    assert calls == [
        (
            engine,
            ticks,
            {
                "position_size": 0.2,
                "commission_per_lot": 7.0,
                "slippage_model": "fixed",
                "slippage_points": 1.0,
                "slippage_min": 0.5,
                "slippage_max": 4.0,
                "monitor_verbose": True,
                "show_progress": False,
                "progress_desc": "Check",
                "frame_observer": "observer",
            },
        )
    ]


def test_event_driven_equity_snapshot_policy_changes_account_sampling():
    bar_close_engine = SnapshotPolicyEngine("bar_close")
    position_update_engine = SnapshotPolicyEngine("position_update")

    run_event_driven_simulation(bar_close_engine, _ticks_with_bar_close())
    run_event_driven_simulation(position_update_engine, _ticks_with_bar_close())

    assert bar_close_engine.monitor_account_calls == 1
    assert position_update_engine.monitor_account_calls == 3
    assert position_update_engine.monitor_positions_calls == 3

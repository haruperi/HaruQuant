from types import SimpleNamespace

import pandas as pd

import backend.services.simulation.engine as engine_module
from backend.services.simulation.engine import Engine
from backend.services.simulation.event_driven import run_event_driven_simulation


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
        )

    def _risk_enabled(self):
        return False


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

    processed = run_event_driven_simulation(engine, _ticks())

    assert processed == 3


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
                "monitor_verbose": True,
                "show_progress": False,
                "progress_desc": "Check",
                "frame_observer": "observer",
            },
        )
    ]

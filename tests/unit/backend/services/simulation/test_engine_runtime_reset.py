from types import SimpleNamespace

import pandas as pd

from backend.services.execution import core
from backend.services.simulation.config import AccountConfig
from backend.services.simulation.engine import Engine


def _make_engine():
    engine = Engine.__new__(Engine)
    engine.backend = "sim"
    engine.mt5_account = SimpleNamespace(leverage=100)
    engine.state = core.SimulatorState(
        account_info={
            "login": 123456,
            "server": "Backtest Simulation Server",
            "company": "HaruQuant",
            "currency": "USD",
            "balance": 5000.0,
            "equity": 5200.0,
            "credit": 100.0,
            "profit": 200.0,
            "margin": 50.0,
            "margin_free": 5150.0,
            "margin_level": 104.0,
            "commission": 3.0,
            "leverage": 50,
        }
    )
    engine.state.trading_deals = [object()]
    engine.state.trading_history_deals = [object()]
    engine.state.trading_orders = [object()]
    engine.state.trading_history_orders = [object()]
    engine.state.completed_trade_records = [object()]
    engine.state.completed_equity_curve = [object()]
    engine.state.equity_peak = 9000.0
    engine.state.open_trade_records_by_ticket = {1: object()}
    engine.state.open_trade_trackers_by_ticket = {1: object()}
    engine.state.current_tick_epoch = 111
    engine.state.current_tick_datetime = pd.Timestamp("2025-01-01 00:00:00")
    engine.state.execution_settings = core.DotDict({"slippage_model": "fixed"})
    engine._risk_equity_history = [(pd.Timestamp("2025-01-01 00:00:00"), 10000.0)]
    engine._schedule_state_dirty = False
    return engine


def test_reset_runtime_reseeds_account_and_clears_runtime_state():
    engine = _make_engine()

    account = engine.reset_runtime(
        AccountConfig(
            initial_balance=10000.0,
            commission=7.0,
            leverage=400,
            currency="USD",
        )
    )

    assert account["login"] == 123456
    assert account["server"] == "Backtest Simulation Server"
    assert account["balance"] == 10000.0
    assert account["credit"] == 0.0
    assert account["profit"] == 0.0
    assert account["equity"] == 10000.0
    assert account["margin"] == 0.0
    assert account["margin_free"] == 10000.0
    assert account["margin_level"] == 0.0
    assert account["commission"] == 7.0
    assert account["leverage"] == 400
    assert account["currency"] == "USD"
    assert engine.state.trading_deals == []
    assert engine.state.trading_history_deals == []
    assert engine.state.trading_orders == []
    assert engine.state.trading_history_orders == []
    assert engine.state.completed_trade_records == []
    assert engine.state.completed_equity_curve == []
    assert engine.state.open_trade_records_by_ticket == {}
    assert engine.state.open_trade_trackers_by_ticket == {}
    assert engine.state.current_tick_epoch is None
    assert engine.state.current_tick_datetime is None
    assert dict(engine.state.execution_settings) == {}
    assert engine._risk_equity_history == []
    assert engine._schedule_state_dirty is True


def test_reset_runtime_requires_account_config():
    engine = _make_engine()

    try:
        engine.reset_runtime({"initial_balance": 10000.0})
    except TypeError as exc:
        assert "AccountConfig" in str(exc)
    else:
        raise AssertionError("reset_runtime should reject non-AccountConfig input")

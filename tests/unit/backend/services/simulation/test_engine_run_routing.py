import pandas as pd
from types import SimpleNamespace

from services.execution import core
from services.simulation import runner as runner_module
from services.simulation.config import SimulationConfig
from services.simulation.data_preparation import SimulationDataPreparer
from services.simulation.engine import Engine
from services.simulation.strategy_registry import register_strategy
from services.strategy.base import BaseStrategy
from services.strategy.stateful import StatefulStrategyMixin, TradeAction


def _config(engine_type="vectorized"):
    return SimulationConfig.from_dict(
        {
            "engine_type": engine_type,
            "account": {"initial_balance": 10000.0},
            "data": {
                "source": "metatrader",
                "symbols": ["AUDUSD"],
                "timeframe": "H1",
                "start": "2025-01-01",
                "end": "2025-01-02",
                "warmup_start": "2024-12-31",
            },
            "strategy": {"name": "FixtureSignalStrategy", "params": {}},
            "execution": {
                "tick_model": "timeframe_ticks",
                "spread_model": "native_spread",
                "contract_size": 100000,
                "position_size": {"type": "fixed_lot", "lot_size": 0.1},
            },
        }
    )


def _prepared():
    return SimpleNamespace(
        ticks=pd.DataFrame(
            {
                "bid": [1.0],
                "ask": [1.0002],
                "symbol": ["AUDUSD"],
                "is_bar_close": [True],
            },
            index=pd.to_datetime(["2025-01-01 00:00:00"]),
        ),
        signal_bars_by_symbol={},
    )


def test_engine_run_routes_config_to_simulation_runner(monkeypatch):
    calls = []

    class FakeRunner:
        def __init__(self, engine):
            calls.append(("init", engine))
            self.engine = engine

        def run(self, config):
            calls.append(("run", config))
            return {"result": "ok"}

    monkeypatch.setattr(runner_module, "SimulationRunner", FakeRunner)
    engine = Engine.__new__(Engine)
    config = _config()

    result = engine.run(config)

    assert result == {"result": "ok"}
    assert calls == [("init", engine), ("run", config)]


def test_engine_run_prepared_routes_vectorized_engine():
    engine = Engine.__new__(Engine)
    calls = []
    sizing_calls = []

    def fake_run_vectorized(
        data,
        initial_balance,
        contract_size,
        position_size,
        commission_per_lot,
        slippage_model,
        slippage_points,
        slippage_min,
        slippage_max,
    ):
        calls.append(
            (
                data,
                initial_balance,
                contract_size,
                position_size,
                commission_per_lot,
                slippage_model,
                slippage_points,
                slippage_min,
                slippage_max,
            )
        )
        return len(data)

    def fake_configure_position_sizing(**kwargs):
        sizing_calls.append(kwargs)

    engine.configure_position_sizing = fake_configure_position_sizing
    engine.run_vectorized = fake_run_vectorized
    prepared = _prepared()
    config = _config("vectorized")

    processed_ticks = engine.run_prepared(prepared, config)

    assert processed_ticks == 1
    assert sizing_calls == [
        {
            "enabled": True,
            "position_sizing_method": "fixed_lot",
            "position_sizing_config": {"lot_size": 0.1},
            "historical_data": {},
        }
    ]
    assert calls == [
        (prepared.ticks, 10000.0, 100000.0, 0.1, 0.0, "none", 0.0, None, None)
    ]


def test_engine_run_prepared_routes_event_driven_engine():
    engine = Engine.__new__(Engine)
    calls = []
    sizing_calls = []

    def fake_run_event_driven(
        data,
        position_size=None,
        commission_per_lot=0.0,
        slippage_model="none",
        slippage_points=0.0,
        slippage_min=None,
        slippage_max=None,
    ):
        calls.append(
            (
                data,
                position_size,
                commission_per_lot,
                slippage_model,
                slippage_points,
                slippage_min,
                slippage_max,
            )
        )
        return len(data)

    def fake_configure_position_sizing(**kwargs):
        sizing_calls.append(kwargs)

    engine.configure_position_sizing = fake_configure_position_sizing
    engine.run_event_driven = fake_run_event_driven
    prepared = _prepared()
    config = _config("event_driven")

    processed_ticks = engine.run_prepared(prepared, config)

    assert processed_ticks == 1
    assert sizing_calls == [
        {
            "enabled": True,
            "position_sizing_method": "fixed_lot",
            "position_sizing_config": {"lot_size": 0.1},
            "historical_data": {},
        }
    ]
    assert calls == [(prepared.ticks, None, 0.0, "none", 0.0, None, None)]


def test_engine_run_prepared_falls_back_to_event_driven_for_dynamic_position_sizing():
    engine = Engine.__new__(Engine)
    vectorized_calls = []
    event_driven_calls = []

    def fake_configure_position_sizing(**kwargs):
        return None

    def fake_run_vectorized(*args, **kwargs):
        vectorized_calls.append((args, kwargs))
        return 0

    def fake_run_event_driven(
        data,
        position_size=None,
        commission_per_lot=0.0,
        slippage_model="none",
        slippage_points=0.0,
        slippage_min=None,
        slippage_max=None,
    ):
        event_driven_calls.append(
            (
                data,
                position_size,
                commission_per_lot,
                slippage_model,
                slippage_points,
                slippage_min,
                slippage_max,
            )
        )
        return len(data)

    engine.configure_position_sizing = fake_configure_position_sizing
    engine.run_vectorized = fake_run_vectorized
    engine.run_event_driven = fake_run_event_driven
    prepared = _prepared()
    config = SimulationConfig.from_dict(
        {
            "engine_type": "vectorized",
            "account": {"initial_balance": 10000.0},
            "data": {
                "source": "metatrader",
                "symbols": ["AUDUSD"],
                "timeframe": "H1",
                "start": "2025-01-01",
                "end": "2025-01-02",
                "warmup_start": "2024-12-31",
            },
            "strategy": {"name": "FixtureSignalStrategy", "params": {}},
            "execution": {
                "tick_model": "timeframe_ticks",
                "spread_model": "native_spread",
                "contract_size": 100000,
                "position_size": {
                    "type": "fixed_percent",
                    "lot_size": 0.1,
                    "risk_percent": 1.0,
                },
            },
        }
    )

    processed_ticks = engine.run_prepared(prepared, config)

    assert processed_ticks == 1
    assert vectorized_calls == []
    assert event_driven_calls == [(prepared.ticks, None, 0.0, "none", 0.0, None, None)]


class FixtureStatefulStrategy(StatefulStrategyMixin):
    pass


class FixtureLegacySignalStrategy(BaseStrategy):
    def on_init(self):
        return None

    def on_bar(self, data):
        out = data.copy()
        out["entry_signal"] = 0
        out["exit_signal"] = 0
        out["pending_signal"] = 0
        out["cancel_pending_signal"] = 0
        out["price"] = 0.0
        out.loc[out.index[1], "entry_signal"] = 1
        out.loc[out.index[2], "exit_signal"] = 1
        out.loc[out.index[[1, 2]], "price"] = out.loc[out.index[[1, 2]], "open"]
        return out


def test_old_signal_strategy_still_generates_signal_columns_unchanged():
    register_strategy("FixtureLegacySignalStrategy", FixtureLegacySignalStrategy)
    bars = pd.DataFrame(
        {
            "open": [1.1000, 1.1010, 1.1020],
            "high": [1.1010, 1.1020, 1.1030],
            "low": [1.0990, 1.1000, 1.1010],
            "close": [1.1005, 1.1015, 1.1025],
            "volume": [100, 110, 120],
        },
        index=pd.to_datetime(
            ["2025-01-01 00:00:00", "2025-01-01 01:00:00", "2025-01-01 02:00:00"]
        ),
    )
    config = SimulationConfig.from_dict(
        {
            "engine_type": "vectorized",
            "account": {"initial_balance": 10000.0},
            "data": {
                "source": "metatrader",
                "symbols": ["AUDUSD"],
                "timeframe": "H1",
                "start": "2025-01-01",
                "end": "2025-01-01 02:00:00",
                "warmup_start": "2025-01-01",
            },
            "strategy": {"name": "FixtureLegacySignalStrategy", "params": {}},
            "execution": {
                "tick_model": "timeframe_ticks",
                "spread_model": "fixed_spread",
                "spread_points": 2.0,
                "contract_size": 100000,
                "position_size": {"type": "fixed_lot", "lot_size": 0.1},
            },
            "preloaded_data": bars,
        }
    )
    engine = Engine.__new__(Engine)
    engine.client = None
    prepared = SimulationDataPreparer(engine).prepare_symbol(config, "AUDUSD")
    signal_bars = prepared.signal_bars_by_symbol["AUDUSD"]

    assert (
        getattr(FixtureLegacySignalStrategy, "requires_portfolio_state", False) is False
    )
    assert signal_bars["entry_signal"].tolist() == [0, 1, 0]
    assert signal_bars["exit_signal"].tolist() == [0, 0, 1]
    assert signal_bars["pending_signal"].tolist() == [0, 0, 0]
    assert signal_bars["cancel_pending_signal"].tolist() == [0, 0, 0]
    assert len(prepared.ticks) > 0


def test_engine_run_prepared_routes_stateful_strategy_to_event_driven():
    engine = Engine.__new__(Engine)
    vectorized_calls = []
    event_driven_calls = []
    runtime_strategy = FixtureStatefulStrategy()

    def fake_configure_position_sizing(**kwargs):
        return None

    def fake_run_vectorized(*args, **kwargs):
        vectorized_calls.append((args, kwargs))
        return 0

    def fake_run_event_driven(
        data,
        position_size=None,
        commission_per_lot=0.0,
        slippage_model="none",
        slippage_points=0.0,
        slippage_min=None,
        slippage_max=None,
        strategy=None,
    ):
        event_driven_calls.append(
            (
                data,
                position_size,
                commission_per_lot,
                slippage_model,
                slippage_points,
                slippage_min,
                slippage_max,
                strategy,
            )
        )
        return len(data)

    engine.configure_position_sizing = fake_configure_position_sizing
    engine.run_vectorized = fake_run_vectorized
    engine.run_event_driven = fake_run_event_driven
    engine._build_runtime_strategy = lambda config: runtime_strategy
    prepared = _prepared()
    config = _config("vectorized")

    processed_ticks = engine.run_prepared(prepared, config)

    assert processed_ticks == 1
    assert vectorized_calls == []
    assert len(event_driven_calls) == 1
    assert isinstance(event_driven_calls[0][-1], FixtureStatefulStrategy)


def test_engine_apply_trade_action_translates_open_to_order_send():
    engine = Engine.__new__(Engine)
    engine.default_signal_volume = 0.1
    engine.position_sizing = {"enabled": False, "position_sizer": None}
    engine.state = core.SimulatorState(
        account_info={"balance": 10000.0, "equity": 10000.0}
    )
    requests = []

    def fake_order_send(request, verbose=False):
        requests.append((request, verbose))
        return SimpleNamespace(retcode=10009)

    engine.order_send = fake_order_send

    changed = engine._apply_trade_action(
        TradeAction(
            action_type="OPEN",
            symbol="AUDUSD",
            side="BUY",
            volume=0.2,
            stop_loss=0.9900,
            take_profit=1.0200,
            reason="unit_test",
        ),
        bid=1.0000,
        ask=1.0002,
    )

    assert changed is True
    assert requests == [
        (
            {
                "action": 1,
                "symbol": "AUDUSD",
                "type": 0,
                "volume": 0.2,
                "price": 1.0002,
                "sl": 0.99,
                "tp": 1.02,
                "comment": "unit_test",
                "external_id": "",
                "setup_id": "",
                "group_id": "",
                "strategy_id": "",
            },
            False,
        )
    ]


def test_engine_open_action_preserves_stateful_group_metadata():
    engine = Engine.__new__(Engine)
    engine.default_signal_volume = 0.1
    engine.position_sizing = {"enabled": False, "position_sizer": None}
    engine.state = core.SimulatorState(
        account_info={"balance": 10000.0, "equity": 10000.0}
    )
    requests = []

    def fake_order_send(request, verbose=False):
        requests.append(request)
        return SimpleNamespace(retcode=10009)

    engine.order_send = fake_order_send

    changed = engine._apply_trade_action(
        TradeAction(
            action_type="OPEN",
            symbol="EURUSD",
            side="SELL",
            volume=0.2,
            setup_id="setup-1",
            group_id="group-1",
            strategy_id="strategy-1",
        ),
        bid=1.1000,
        ask=1.1002,
    )

    assert changed is True
    assert requests[0]["external_id"] == "group-1"
    assert requests[0]["setup_id"] == "setup-1"
    assert requests[0]["group_id"] == "group-1"
    assert requests[0]["strategy_id"] == "strategy-1"


def _guarded_engine(*, controls=None, balance=10000.0, equity=10000.0):
    engine = Engine.__new__(Engine)
    engine.default_signal_volume = 0.1
    engine.position_sizing = {"enabled": False, "position_sizer": None}
    engine.state = core.SimulatorState(
        account_info={"balance": balance, "equity": equity}
    )
    engine.stateful_risk_controls = {"enabled": True, **(controls or {})}
    engine.stateful_guardrail_state = {
        "seen_batches": set(),
        "equity_peaks": {},
        "violations": [],
    }
    requests = []

    def fake_order_send(request, verbose=False):
        requests.append((request, verbose))
        return SimpleNamespace(retcode=10009)

    engine.order_send = fake_order_send
    engine.account_info = lambda: engine.state.trading_account
    return engine, requests


def _open_position(ticket, *, symbol="AUDUSD", volume=0.1, group_id="", comment=""):
    return SimpleNamespace(
        ticket=ticket,
        position_id=ticket,
        entry=0,
        symbol=symbol,
        type=0,
        volume=volume,
        price_open=1.0,
        price_current=1.0,
        sl=0.0,
        tp=0.0,
        group_id=group_id,
        setup_id=group_id,
        external_id=group_id,
        comment=comment,
    )


def test_stateful_risk_controls_block_open_positions_above_limit():
    engine, requests = _guarded_engine(controls={"max_open_positions_per_strategy": 1})
    engine.state.trading_deals = [_open_position(1)]

    changed = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="OPEN",
                symbol="AUDUSD",
                side="BUY",
                volume=0.1,
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=1,
    )

    assert changed is False
    assert requests == []
    assert engine.stateful_guardrail_state["violations"][0]["code"] == (
        "max_open_positions_per_strategy"
    )


def test_stateful_risk_controls_allow_close_when_exposure_limit_is_hit():
    engine, requests = _guarded_engine(controls={"max_total_lots": 0.1})
    engine.state.trading_deals = [_open_position(1, volume=0.1)]

    changed = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="CLOSE",
                symbol="AUDUSD",
                side="BUY",
                ticket=1,
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=1,
    )

    assert changed is True
    assert requests[0][0]["action"] == 1
    assert requests[0][0]["position"] == 1


def test_stateful_risk_controls_enforce_layer_step_lot_and_exposure_limits():
    engine, requests = _guarded_engine(
        controls={
            "max_layers_per_setup": 1,
            "max_martingale_step": 2,
            "max_total_lots": 0.2,
            "max_symbol_exposure": 0.2,
        },
    )
    engine.state.trading_deals = [_open_position(1, volume=0.1, group_id="setup-1")]

    layer_blocked = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="OPEN",
                symbol="AUDUSD",
                side="BUY",
                volume=0.1,
                group_id="setup-1",
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=1,
    )
    step_blocked = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="OPEN",
                symbol="AUDUSD",
                side="BUY",
                volume=0.1,
                group_id="setup-2",
                metadata={"martingale_step": 3},
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=2,
    )
    total_lots_blocked = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="OPEN",
                symbol="AUDUSD",
                side="BUY",
                volume=0.2,
                group_id="setup-2",
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=3,
    )

    assert layer_blocked is False
    assert step_blocked is False
    assert total_lots_blocked is False
    assert requests == []
    assert {
        violation["code"] for violation in engine.stateful_guardrail_state["violations"]
    } == {"max_layers_per_setup", "max_martingale_step", "max_total_lots"}


def test_stateful_risk_controls_enforce_symbol_exposure_and_drawdown_limits():
    engine, requests = _guarded_engine(
        controls={
            "max_total_lots": 10.0,
            "max_symbol_exposure": 0.2,
            "max_strategy_drawdown": 50.0,
        },
        balance=10000.0,
        equity=10000.0,
    )
    engine.state.trading_deals = [_open_position(1, volume=0.15)]

    exposure_blocked = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="OPEN",
                symbol="AUDUSD",
                side="BUY",
                volume=0.1,
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=1,
    )

    engine.state.trading_deals = []
    engine.state.trading_account["equity"] = 9900.0
    engine.stateful_guardrail_state["equity_peaks"]["stateful"] = 10000.0
    drawdown_blocked = engine._apply_trade_actions(
        [
            TradeAction(
                action_type="OPEN",
                symbol="AUDUSD",
                side="BUY",
                volume=0.1,
            )
        ],
        bid=1.0,
        ask=1.0002,
        strategy_id="stateful",
        event_key=2,
    )

    assert exposure_blocked is False
    assert drawdown_blocked is False
    assert requests == []
    assert {
        violation["code"] for violation in engine.stateful_guardrail_state["violations"]
    } == {"max_symbol_exposure", "max_strategy_drawdown"}


def test_stateful_risk_controls_block_repeated_action_batch_for_same_event():
    engine, requests = _guarded_engine()
    action = TradeAction(
        action_type="OPEN",
        symbol="AUDUSD",
        side="BUY",
        volume=0.1,
    )

    first = engine._apply_trade_actions(
        [action], bid=1.0, ask=1.0002, strategy_id="stateful", event_key=99
    )
    second = engine._apply_trade_actions(
        [action], bid=1.0, ask=1.0002, strategy_id="stateful", event_key=99
    )

    assert first is True
    assert second is False
    assert len(requests) == 1
    assert engine.stateful_guardrail_state["violations"][0]["code"] == (
        "one_action_batch_per_event"
    )

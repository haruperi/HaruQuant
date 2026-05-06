from services.strategy import (
    PositionSnapshot,
    StatefulStrategyMixin,
    StrategyContext,
    StrategyRuntimeState,
    TradeAction,
)
from services.strategy.compat_types import TradeAction as CompatTradeAction


def test_stateful_strategy_mixin_defaults_to_no_actions():
    class ExampleStrategy(StatefulStrategyMixin):
        pass

    strategy = ExampleStrategy()
    context = StrategyContext(strategy_id="example", symbol="EURUSD")

    assert strategy.requires_portfolio_state is True
    assert strategy.on_event(context) == []


def test_strategy_context_filters_positions_by_symbol():
    context = StrategyContext(
        strategy_id="example",
        symbol="EURUSD",
        runtime_state=StrategyRuntimeState(strategy_id="example"),
        positions=[
            PositionSnapshot(
                ticket=1,
                symbol="EURUSD",
                side="BUY",
                volume=0.1,
                open_price=1.1000,
            ),
            PositionSnapshot(
                ticket=2,
                symbol="GBPUSD",
                side="SELL",
                volume=0.2,
                open_price=1.2500,
            ),
        ],
    )

    assert [position.ticket for position in context.positions_for_symbol()] == [1]
    assert [position.ticket for position in context.positions_for_symbol("GBPUSD")] == [
        2
    ]


def test_trade_action_hold_factory_and_compat_export():
    action = TradeAction.hold(
        symbol="EURUSD",
        strategy_id="example",
        reason="waiting_for_next_bar",
    )

    assert action.action_type == "HOLD"
    assert action.symbol == "EURUSD"
    assert action.strategy_id == "example"
    assert action.reason == "waiting_for_next_bar"
    assert CompatTradeAction is TradeAction

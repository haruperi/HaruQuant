import pandas as pd

from data.strategies.pyramiding import PyramidingStrategy
from data.strategies.rsi_averaging_pyramid import RsiAveragingPyramidStrategy
from data.strategies.rsi_decomposing_reentry import RsiDecomposingReentryStrategy
from data.strategies.rsi_martingale import RsiMartingaleStrategy
from data.strategies.mtf_hedge_trail import StructureHedgeTrailStrategy
from data.strategies.market_structure_hedge_grid import (
    MarketStructureHedgeGridStrategy,
)
from data.strategies.trade_decomposition import TradeDecompositionStrategy
from services.strategy.stateful import OrderSnapshot, PositionSnapshot, StrategyContext


def _context(prices, *, positions=None, account=None):
    index = pd.date_range("2025-01-01", periods=len(prices), freq="min")
    data = pd.DataFrame(
        {
            "bid": prices,
            "ask": [price + 0.0002 for price in prices],
            "symbol": "EURUSD",
            "is_bar_close": "close",
        },
        index=index,
    )
    return StrategyContext(
        strategy_id="test",
        symbol="EURUSD",
        timestamp=index[-1],
        current_tick=data.iloc[-1].to_dict(),
        market_data=data,
        account=account or {},
        positions=positions or [],
        metadata={"tick_index": len(data) - 1},
    )


def _ohlc_context(bars, *, positions=None, account=None):
    rows = []
    index = []
    for bar_time, open_price, high_price, low_price, close_price in bars:
        bullish = close_price >= open_price
        path = (
            [open_price, low_price, high_price, close_price]
            if bullish
            else [open_price, high_price, low_price, close_price]
        )
        phases = [
            "open",
            "low" if bullish else "high",
            "high" if bullish else "low",
            "close",
        ]
        for offset, (price, phase) in enumerate(zip(path, phases)):
            rows.append(
                {
                    "bid": price,
                    "ask": price + 0.0002,
                    "symbol": "EURUSD",
                    "source_bar_time": bar_time,
                    "is_bar_close": phase,
                }
            )
            index.append(pd.Timestamp(bar_time) + pd.Timedelta(seconds=offset))
    data = pd.DataFrame(rows, index=pd.DatetimeIndex(index))
    return StrategyContext(
        strategy_id="test",
        symbol="EURUSD",
        timestamp=data.index[-1],
        current_tick=data.iloc[-1].to_dict(),
        market_data=data,
        account=account or {},
        positions=positions or [],
        metadata={"tick_index": len(data) - 1},
    )


def _structure_buy_bars():
    start = pd.Timestamp("2025-01-01 00:00")
    bars = []
    for i in range(12):
        ts = start + pd.Timedelta(minutes=5 * i)
        bars.append((ts, 1.1000, 1.1020, 1.0950 + i * 0.00001, 1.1010))
    for i in range(10):
        ts = start + pd.Timedelta(hours=1, minutes=5 * i)
        bars.append((ts, 1.1030, 1.1060, 1.1010 + i * 0.00005, 1.1040))
    bars.append(
        (start + pd.Timedelta(hours=1, minutes=50), 1.1040, 1.1060, 1.1020, 1.1050)
    )
    bars.append(
        (start + pd.Timedelta(hours=1, minutes=55), 1.1050, 1.1070, 1.1030, 1.1060)
    )
    return bars


def _structure_sell_bars():
    start = pd.Timestamp("2025-01-01 00:00")
    bars = []
    for i in range(12):
        ts = start + pd.Timedelta(minutes=5 * i)
        bars.append((ts, 1.1050, 1.1100 - i * 0.00001, 1.1020, 1.1040))
    for i in range(10):
        ts = start + pd.Timedelta(hours=1, minutes=5 * i)
        bars.append((ts, 1.1030, 1.1080 - i * 0.00005, 1.1000, 1.1020))
    bars.append(
        (start + pd.Timedelta(hours=1, minutes=50), 1.1020, 1.1070, 1.1000, 1.1010)
    )
    bars.append(
        (start + pd.Timedelta(hours=1, minutes=55), 1.1010, 1.1060, 1.0990, 1.1000)
    )
    return bars


def _buy_position(
    *,
    ticket=1,
    volume=0.1,
    open_price=1.1000,
    current_price=1.0960,
    stop_loss=None,
    take_profit=None,
    profit_loss=0.0,
    setup_id=None,
    metadata=None,
):
    return PositionSnapshot(
        ticket=ticket,
        symbol="EURUSD",
        side="BUY",
        volume=volume,
        open_price=open_price,
        current_price=current_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        profit_loss=profit_loss,
        opened_at=f"2025-01-01T00:0{ticket}:00",
        setup_id=setup_id,
        metadata=metadata or {},
    )


def _sell_position(
    *,
    ticket=1,
    volume=0.1,
    open_price=1.1000,
    current_price=1.1040,
    profit_loss=0.0,
    setup_id=None,
    metadata=None,
):
    return PositionSnapshot(
        ticket=ticket,
        symbol="EURUSD",
        side="SELL",
        volume=volume,
        open_price=open_price,
        current_price=current_price,
        profit_loss=profit_loss,
        opened_at=f"2025-01-01T00:0{ticket}:00",
        setup_id=setup_id,
        metadata=metadata or {},
    )


def _pending_order(
    *,
    ticket=10,
    side="BUY",
    order_type="LIMIT",
    volume=0.1,
    price=1.1000,
    metadata=None,
):
    return OrderSnapshot(
        ticket=ticket,
        symbol="EURUSD",
        side=side,
        order_type=order_type,
        volume=volume,
        price=price,
        metadata=metadata or {},
    )


def test_martingale_increases_size_after_loss():
    strategy = RsiMartingaleStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "rsi_oversold": 35,
            "initial_lot": 0.1,
            "multiplier": 2.0,
            "min_step_pips": 5,
        }
    )
    strategy.on_init()
    strategy.state["buy"] = {"last_price": 1.1000, "total_vol": 0.1, "steps": 1}

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0990, 1.0980, 1.0970, 1.0960],
            positions=[_buy_position()],
        )
    )

    assert len(actions) == 1
    assert actions[0].action_type == "OPEN"
    assert actions[0].side == "BUY"
    assert actions[0].volume == 0.2
    assert strategy.state["buy"]["steps"] == 2


def test_martingale_resets_after_win():
    strategy = RsiMartingaleStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "rsi_oversold": 35,
            "target_profit_usd": 5.0,
        }
    )
    strategy.on_init()
    strategy.state["buy"] = {"last_price": 1.0960, "total_vol": 0.3, "steps": 3}

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0990, 1.0980, 1.0970, 1.0960],
            positions=[_buy_position(profit_loss=6.0)],
        )
    )

    assert [action.action_type for action in actions] == ["CLOSE_GROUP"]
    assert actions[0].side == "BUY"
    assert strategy.state["buy"] == {"last_price": 0.0, "total_vol": 0.0, "steps": 0}


def test_martingale_respects_max_steps_and_max_lot():
    strategy = RsiMartingaleStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "rsi_oversold": 35,
            "multiplier": 3.0,
            "min_step_pips": 5,
            "max_steps": 2,
            "max_lot": 0.25,
        }
    )
    strategy.on_init()
    strategy.state["buy"] = {"last_price": 1.1000, "total_vol": 0.1, "steps": 1}

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0990, 1.0980, 1.0970, 1.0960],
            positions=[_buy_position()],
        )
    )

    assert actions[0].volume == 0.25

    strategy.state["buy"] = {"last_price": 1.1000, "total_vol": 0.25, "steps": 2}
    actions = strategy.on_event(
        _context(
            [1.1000, 1.0990, 1.0980, 1.0970, 1.0960],
            positions=[_buy_position(volume=0.25)],
        )
    )

    assert actions == []


def test_pyramiding_adds_layers_only_when_position_profitable():
    strategy = PyramidingStrategy(
        params={
            "symbol": "EURUSD",
            "fast_ma_period": 2,
            "slow_ma_period": 3,
            "initial_lot": 1.0,
            "min_step_pips": 5,
            "trailing_sl_pips": 2,
        }
    )
    strategy.on_init()
    strategy.state["buy"] = {"last_price": 1.1000, "total_positions": 1}

    actions = strategy.on_event(
        _context(
            [1.1000, 1.1010, 1.1020, 1.1030],
            positions=[
                _buy_position(volume=1.0, open_price=1.1000, current_price=1.1030)
            ],
        )
    )

    assert [action.action_type for action in actions] == ["OPEN", "MODIFY_SL"]
    assert actions[0].volume == 0.5
    assert actions[1].side == "BUY"


def test_pyramiding_respects_max_layers():
    strategy = PyramidingStrategy(
        params={
            "symbol": "EURUSD",
            "fast_ma_period": 2,
            "slow_ma_period": 3,
            "initial_lot": 1.0,
            "min_step_pips": 5,
            "max_positions_per_side": 1,
        }
    )
    strategy.on_init()
    strategy.state["buy"] = {"last_price": 1.1000, "total_positions": 1}

    actions = strategy.on_event(
        _context(
            [1.1000, 1.1010, 1.1020, 1.1030],
            positions=[
                _buy_position(volume=1.0, open_price=1.1000, current_price=1.1030)
            ],
        )
    )

    assert actions == []


def test_pyramiding_does_not_add_when_flat_or_losing():
    strategy = PyramidingStrategy(
        params={
            "symbol": "EURUSD",
            "fast_ma_period": 2,
            "slow_ma_period": 3,
            "initial_lot": 1.0,
            "min_step_pips": 5,
        }
    )
    strategy.on_init()
    strategy.state["buy"] = {"last_price": 1.1000, "total_positions": 1}

    losing_actions = strategy.on_event(
        _context(
            [1.1000, 1.1010, 1.1020, 1.1030],
            positions=[
                _buy_position(volume=1.0, open_price=1.1040, current_price=1.1030)
            ],
        )
    )

    assert losing_actions == []

    flat_actions = strategy.on_event(_context([1.1000, 1.1010, 1.1020, 1.1030]))

    assert [action.action_type for action in flat_actions] == ["OPEN"]
    assert flat_actions[0].reason == "Initial BUY pyramiding trend entry"


def test_decomposition_opens_child_trades():
    strategy = TradeDecompositionStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "os_level": 35,
            "trade_distance": 5,
            "vol_decrease": 0.02,
            "initial_lot": 0.06,
        }
    )
    strategy.on_init()
    strategy.state["previous_rsi"] = 20.0

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0990, 1.0980, 1.0970, 1.0960],
            positions=[_buy_position(volume=0.06, setup_id="group-1")],
        )
    )

    assert [action.action_type for action in actions] == ["REDUCE", "OPEN", "MODIFY_TP"]
    assert actions[0].ticket == 1
    assert actions[0].volume == 0.02
    assert actions[1].volume == 0.08
    assert actions[1].metadata == {"role": "child", "parent_ticket": 1}


def test_decomposition_closes_first_child_at_tp():
    strategy = TradeDecompositionStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "child_take_profit_pips": 5,
        }
    )
    strategy.on_init()
    child = _buy_position(
        ticket=2,
        volume=0.08,
        open_price=1.0960,
        current_price=1.0970,
        setup_id="group-1",
        metadata={"role": "child", "group_id": "group-1"},
    )

    actions = strategy.on_event(
        _context(
            [1.0960, 1.0965, 1.0970, 1.0972, 1.0975],
            positions=[child],
        )
    )

    assert actions[0].action_type == "CLOSE"
    assert actions[0].ticket == 2
    assert actions[0].group_id == "group-1"


def test_decomposition_moves_remaining_trade_to_breakeven():
    strategy = TradeDecompositionStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "child_take_profit_pips": 5,
        }
    )
    strategy.on_init()
    parent = _buy_position(
        ticket=1,
        volume=0.06,
        open_price=1.0950,
        current_price=1.0975,
        setup_id="group-1",
        metadata={"role": "parent", "group_id": "group-1"},
    )
    child = _buy_position(
        ticket=2,
        volume=0.08,
        open_price=1.0960,
        current_price=1.0975,
        setup_id="group-1",
        metadata={"role": "child", "group_id": "group-1"},
    )

    actions = strategy.on_event(
        _context(
            [1.0960, 1.0965, 1.0970, 1.0972, 1.0975],
            positions=[parent, child],
        )
    )

    assert [action.action_type for action in actions] == ["CLOSE", "MOVE_TO_BREAKEVEN"]
    assert actions[1].ticket == 1
    assert actions[1].group_id == "group-1"


def test_decomposition_preserves_group_id_or_setup_id():
    strategy = TradeDecompositionStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 3,
            "os_level": 35,
            "trade_distance": 5,
            "vol_decrease": 0.02,
            "initial_lot": 0.06,
        }
    )
    strategy.on_init()
    strategy.state["previous_rsi"] = 20.0

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0990, 1.0980, 1.0970, 1.0960],
            positions=[
                _buy_position(
                    volume=0.06,
                    setup_id="setup-42",
                    metadata={"group_id": "basket-42"},
                )
            ],
        )
    )

    assert {action.group_id for action in actions} == {"basket-42"}
    assert {action.setup_id for action in actions} == {"basket-42"}


def test_rsi_averaging_pyramid_opens_initial_buy_with_dynamic_lot():
    strategy = RsiAveragingPyramidStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "os_level": 20,
            "balance_increase": 2000,
            "volume_increase": 0.01,
            "lot_divisor": 2,
            "cost_averaging_distance_pips": 10,
            "pyramiding_distance_pips": 10,
        }
    )
    strategy.on_init()

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0900, 1.0800, 1.0810, 1.0820],
            account={"balance": 10000.0},
        )
    )

    assert [action.action_type for action in actions] == ["OPEN"]
    assert actions[0].side == "BUY"
    assert actions[0].volume == 0.05
    assert actions[0].reason == "FirstBuy"
    assert strategy.state["buy"]["cost_averaging_lot"] == 0.05
    assert strategy.state["buy"]["pyramiding_lot"] == 0.03


def test_rsi_averaging_pyramid_cost_averages_and_moves_tp_to_simple_average():
    strategy = RsiAveragingPyramidStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "os_level": 20,
            "initial_lot": 0.1,
            "cost_averaging_distance_pips": 10,
        }
    )
    strategy.on_init()
    strategy.state["buy"].update(
        {
            "cost_averaging_lot": 0.1,
            "next_cost_averaging_price": 1.0990,
            "next_pyramiding_price": 1.1010,
        }
    )

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0900, 1.0800, 1.0810, 1.0820],
            positions=[_buy_position(open_price=1.1000, current_price=1.0820)],
        )
    )

    assert [action.action_type for action in actions] == [
        "OPEN",
        "MODIFY_SL",
        "MODIFY_TP",
    ]
    assert actions[0].reason == "C.Averaging Buy"
    assert actions[0].volume == 0.1
    assert actions[1].stop_loss == 0.0
    assert actions[2].take_profit == 1.0911


def test_rsi_averaging_pyramid_pyramids_winners_and_clears_tp():
    strategy = RsiAveragingPyramidStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "initial_lot": 0.1,
            "pyramiding_distance_pips": 10,
            "sl_displacement_pips": 5,
            "lot_divisor": 2,
        }
    )
    strategy.on_init()
    strategy.state["buy"].update(
        {
            "pyramiding_lot": 0.05,
            "next_pyramiding_price": 1.1010,
            "next_cost_averaging_price": 1.0990,
        }
    )

    actions = strategy.on_event(
        _context(
            [1.1000, 1.1010, 1.1020, 1.1030, 1.1040],
            positions=[_buy_position(open_price=1.1000, current_price=1.1040)],
        )
    )

    assert [action.action_type for action in actions] == [
        "OPEN",
        "MODIFY_SL",
        "MODIFY_TP",
    ]
    assert actions[0].reason == "Pyramid Buy"
    assert actions[0].volume == 0.05
    assert actions[1].stop_loss == 1.1037
    assert actions[2].take_profit == 0.0
    assert strategy.state["buy"]["pyramiding_lot"] == 0.03


def test_rsi_averaging_pyramid_opens_initial_sell():
    strategy = RsiAveragingPyramidStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "ob_level": 80,
            "initial_lot": 0.1,
        }
    )
    strategy.on_init()

    actions = strategy.on_event(_context([1.1000, 1.1100, 1.1200, 1.1190, 1.1180]))

    assert [action.action_type for action in actions] == ["OPEN"]
    assert actions[0].side == "SELL"
    assert actions[0].reason == "FirstSell"


def test_rsi_averaging_pyramid_is_registered():
    from services.simulation.strategy_registry import get_strategy_class

    assert (
        get_strategy_class("RsiAveragingPyramidStrategy") is RsiAveragingPyramidStrategy
    )


def test_structure_hedge_trail_opens_buy_on_multi_timeframe_higher_low():
    strategy = StructureHedgeTrailStrategy(
        params={
            "symbol": "EURUSD",
            "higher_timeframe": "H1",
            "lower_timeframe": "M5",
            "ht_min_distance_pips": 5,
            "lt_min_distance_pips": 2,
            "take_profit_pips": 30,
            "balance_increase": 3000,
            "volume_increase": 0.01,
        }
    )
    strategy.on_init()

    actions = strategy.on_event(
        _ohlc_context(_structure_buy_bars(), account={"balance": 9000.0})
    )

    assert [action.action_type for action in actions] == ["OPEN"]
    assert actions[0].side == "BUY"
    assert actions[0].volume == 0.03
    assert actions[0].take_profit == 1.1092
    assert strategy.state["bought"] is True
    assert strategy.state["sold"] is False


def test_structure_hedge_trail_opens_sell_on_multi_timeframe_lower_high():
    strategy = StructureHedgeTrailStrategy(
        params={
            "symbol": "EURUSD",
            "higher_timeframe": "H1",
            "lower_timeframe": "M5",
            "ht_min_distance_pips": 5,
            "lt_min_distance_pips": 2,
            "take_profit_pips": 30,
            "initial_lot": 0.1,
        }
    )
    strategy.on_init()

    actions = strategy.on_event(_ohlc_context(_structure_sell_bars()))

    assert [action.action_type for action in actions] == ["OPEN"]
    assert actions[0].side == "SELL"
    assert actions[0].volume == 0.1
    assert actions[0].take_profit == 1.097
    assert strategy.state["sold"] is True
    assert strategy.state["bought"] is False


def test_structure_hedge_trail_bought_flag_blocks_repeated_buy_until_flat():
    strategy = StructureHedgeTrailStrategy(
        params={
            "symbol": "EURUSD",
            "higher_timeframe": "H1",
            "lower_timeframe": "M5",
        }
    )
    strategy.on_init()
    strategy.state["bought"] = True

    blocked = strategy.on_event(_ohlc_context(_structure_buy_bars()))
    assert blocked == []
    assert strategy.state["bought"] is False


def test_structure_hedge_trail_moves_multi_position_buy_tp_to_simple_average():
    strategy = StructureHedgeTrailStrategy(
        params={
            "symbol": "EURUSD",
            "higher_timeframe": "H1",
            "lower_timeframe": "M5",
        }
    )
    strategy.on_init()
    positions = [
        _buy_position(ticket=1, open_price=1.1000, current_price=1.0900, volume=0.1),
        _buy_position(ticket=2, open_price=1.1040, current_price=1.0900, volume=0.3),
    ]

    actions = strategy.on_event(
        _ohlc_context(_structure_sell_bars(), positions=positions)
    )

    modify_actions = [
        action for action in actions if action.action_type in {"MODIFY_SL", "MODIFY_TP"}
    ]
    assert [action.action_type for action in modify_actions] == [
        "MODIFY_SL",
        "MODIFY_TP",
        "MODIFY_SL",
        "MODIFY_TP",
    ]
    assert {
        action.take_profit
        for action in modify_actions
        if action.action_type == "MODIFY_TP"
    } == {1.102}


def test_structure_hedge_trail_trails_single_buy_sl_to_previous_lower_bar_low():
    strategy = StructureHedgeTrailStrategy(
        params={
            "symbol": "EURUSD",
            "higher_timeframe": "H1",
            "lower_timeframe": "M5",
            "when_to_trail_pips": 10,
        }
    )
    strategy.on_init()
    position = _buy_position(
        ticket=1,
        open_price=1.1000,
        current_price=1.1060,
        stop_loss=1.1010,
        volume=0.1,
    )

    actions = strategy.on_event(
        _ohlc_context(_structure_buy_bars(), positions=[position])
    )

    sl_actions = [action for action in actions if action.action_type == "MODIFY_SL"]
    assert sl_actions[-1].ticket == 1
    assert sl_actions[-1].stop_loss == 1.103


def test_structure_hedge_trail_is_registered():
    from services.simulation.strategy_registry import get_strategy_class

    assert (
        get_strategy_class("StructureHedgeTrailStrategy") is StructureHedgeTrailStrategy
    )


def test_rsi_decomposing_reentry_opens_first_buy_and_sets_subtract_lot():
    strategy = RsiDecomposingReentryStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "os_level": 20,
            "balance_increase": 3000,
            "volume_increase": 0.06,
            "volume_decrease": 0.02,
        }
    )
    strategy.on_init()

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0900, 1.0800, 1.0810, 1.0820],
            account={"balance": 3000.0},
        )
    )

    assert [action.action_type for action in actions] == ["OPEN"]
    assert actions[0].side == "BUY"
    assert actions[0].volume == 0.06
    assert actions[0].reason == "FBuy"
    assert strategy.state["buy_lot"] == 0.06
    assert strategy.state["buy_lot_subtract"] == 0.02


def test_rsi_decomposing_reentry_opens_buy_hedge_against_existing_sell():
    strategy = RsiDecomposingReentryStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "ob_level": 80,
            "initial_lot": 0.06,
        }
    )
    strategy.on_init()

    actions = strategy.on_event(
        _context(
            [1.1000, 1.1100, 1.1200, 1.1170, 1.1210],
            positions=[_sell_position(open_price=1.1200, current_price=1.1190)],
        )
    )

    assert [action.action_type for action in actions] == ["OPEN"]
    assert actions[0].side == "BUY"
    assert actions[0].reason == "FBuy"


def test_rsi_decomposing_reentry_trails_sl_only_when_no_child_trade_exists():
    strategy = RsiDecomposingReentryStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "when_to_trail_pips": 20,
            "trail_by_pips": 10,
        }
    )
    strategy.on_init()
    parent = _buy_position(
        ticket=1,
        open_price=1.1000,
        current_price=1.1040,
        stop_loss=1.1010,
    )

    actions = strategy.on_event(
        _context([1.1000, 1.1010, 1.1020, 1.1030], positions=[parent])
    )

    assert [action.action_type for action in actions] == ["MODIFY_SL"]
    assert actions[0].stop_loss == 1.103

    child = _buy_position(
        ticket=2,
        open_price=1.0980,
        current_price=1.1040,
        metadata={"comment": "CBuy"},
    )
    actions = strategy.on_event(
        _context([1.1000, 1.1010, 1.1020, 1.1030], positions=[parent, child])
    )

    assert [action for action in actions if action.action_type == "MODIFY_SL"] == []


def test_rsi_decomposing_reentry_partial_closes_worst_buy_and_sets_weighted_tp():
    strategy = RsiDecomposingReentryStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "os_level": 20,
            "initial_lot": 0.06,
            "volume_increase": 0.06,
            "volume_decrease": 0.02,
            "trade_distance_pips": 10,
            "trail_by_pips": 10,
        }
    )
    strategy.on_init()
    strategy.state["buy_lot"] = 0.06
    strategy.state["buy_lot_subtract"] = 0.02
    positions = [
        _buy_position(ticket=1, volume=0.06, open_price=1.1000, current_price=1.0820),
        _buy_position(ticket=2, volume=0.06, open_price=1.0980, current_price=1.0820),
    ]

    actions = strategy.on_event(
        _context(
            [1.1000, 1.0900, 1.0800, 1.0810, 1.0820],
            positions=positions,
        )
    )

    assert [action.action_type for action in actions] == [
        "REDUCE",
        "OPEN",
        "MODIFY_SL",
        "MODIFY_TP",
    ]
    assert actions[0].ticket == 1
    assert actions[0].volume == 0.02
    assert actions[1].volume == 0.1
    assert actions[1].reason == "CBuy"
    assert actions[3].take_profit == 1.0915


def test_rsi_decomposing_reentry_sell_decomposition_uses_lowest_sell_target():
    strategy = RsiDecomposingReentryStrategy(
        params={
            "symbol": "EURUSD",
            "rsi_period": 2,
            "ob_level": 80,
            "initial_lot": 0.06,
            "volume_increase": 0.06,
            "volume_decrease": 0.02,
            "trade_distance_pips": 10,
            "trail_by_pips": 10,
        }
    )
    strategy.on_init()
    strategy.state["sell_lot"] = 0.06
    strategy.state["sell_lot_subtract"] = 0.02
    positions = [
        _sell_position(ticket=1, volume=0.06, open_price=1.1000, current_price=1.1180),
        _sell_position(ticket=2, volume=0.06, open_price=1.1020, current_price=1.1180),
    ]

    actions = strategy.on_event(
        _context(
            [1.1000, 1.1100, 1.1200, 1.1190, 1.1180],
            positions=positions,
        )
    )

    assert actions[0].action_type == "REDUCE"
    assert actions[0].ticket == 1
    assert actions[1].reason == "CSell"
    assert actions[3].take_profit == 1.1086


def test_rsi_decomposing_reentry_is_registered():
    from services.simulation.strategy_registry import get_strategy_class

    assert (
        get_strategy_class("RsiDecomposingReentryStrategy")
        is RsiDecomposingReentryStrategy
    )


def _market_structure_strategy_with_zz(zz):
    strategy = MarketStructureHedgeGridStrategy(
        params={
            "symbol": "EURUSD",
            "zigzag_depth": 3,
            "zigzag_deviation": 1,
            "balance_increase": 3000,
            "volume_increase": 0.04,
            "hedge_displacement_pips": 2,
            "profit_factor": 2.0,
        }
    )
    strategy.on_init()
    strategy._zz_values = lambda bars: zz
    return strategy


def _market_structure_context(*, positions=None, account=None, orders=None):
    context = _ohlc_context(_structure_buy_bars(), positions=positions, account=account)
    context.current_tick = {
        **context.current_tick,
        "is_bar_close": "open",
        "source_bar_time": pd.Timestamp(context.current_tick["source_bar_time"])
        + pd.Timedelta(minutes=5),
    }
    context.orders = orders or []
    return context


def test_market_structure_hedge_grid_opens_first_buy_and_hedge_stop():
    strategy = _market_structure_strategy_with_zz(
        {
            "high0": 1.1070,
            "low0": 1.1030,
            "high1": 1.1055,
            "low1": 1.0990,
            "high2": 1.1040,
            "low2": 1.1000,
            "high3": 1.1060,
            "low3": 1.0980,
        }
    )

    actions = strategy.on_event(_market_structure_context(account={"balance": 3000.0}))

    assert [action.action_type for action in actions] == ["OPEN", "PLACE_PENDING"]
    assert actions[0].side == "BUY"
    assert actions[0].volume == 0.04
    assert actions[0].reason == "FirstBuy"
    assert actions[0].take_profit == 1.113
    assert actions[1].side == "SELL"
    assert actions[1].order_type == "STOP"
    assert actions[1].price == 1.1028
    assert actions[1].take_profit == 1.096
    assert actions[1].reason == "HedgeSell"
    assert strategy.state["next_buy_price"] == 1.096
    assert strategy.state["next_sell_price"] == 1.113


def test_market_structure_hedge_grid_opens_first_sell_and_hedge_stop():
    strategy = _market_structure_strategy_with_zz(
        {
            "high0": 1.1000,
            "low0": 1.0980,
            "high1": 1.1060,
            "low1": 1.1005,
            "high2": 1.1040,
            "low2": 1.1020,
            "high3": 1.1050,
            "low3": 1.0990,
        }
    )

    context = _ohlc_context(_structure_sell_bars())
    context.current_tick = {
        **context.current_tick,
        "is_bar_close": "open",
        "source_bar_time": pd.Timestamp(context.current_tick["source_bar_time"])
        + pd.Timedelta(minutes=5),
    }
    actions = strategy.on_event(context)

    assert [action.action_type for action in actions] == ["OPEN", "PLACE_PENDING"]
    assert actions[0].side == "SELL"
    assert actions[0].reason == "FirstSell"
    assert actions[0].take_profit == 1.0996
    assert actions[1].side == "BUY"
    assert actions[1].order_type == "STOP"
    assert actions[1].price == 1.1002
    assert actions[1].take_profit == 1.1006


def test_market_structure_hedge_grid_places_cost_average_limits_when_hedged():
    strategy = MarketStructureHedgeGridStrategy(params={"symbol": "EURUSD"})
    strategy.on_init()
    strategy.state["buy_lot_used"] = 0.04
    strategy.state["sell_lot_used"] = 0.04
    strategy.state["next_buy_price"] = 1.0960
    strategy.state["next_sell_price"] = 1.1130
    strategy.state["buy_hedge_distance"] = 0.0068
    positions = [
        _buy_position(metadata={"comment": "FirstBuy"}),
        _sell_position(ticket=2, metadata={"comment": "HedgeSell"}),
    ]

    actions = strategy.on_event(_market_structure_context(positions=positions))

    assert [action.action_type for action in actions] == [
        "PLACE_PENDING",
        "PLACE_PENDING",
    ]
    assert actions[0].side == "BUY"
    assert actions[0].order_type == "LIMIT"
    assert actions[0].price == 1.096
    assert actions[0].reason == "CABuy"
    assert actions[1].side == "SELL"
    assert actions[1].order_type == "LIMIT"
    assert actions[1].price == 1.113
    assert actions[1].reason == "CASell"
    assert strategy.state["next_buy_price"] == 1.0892
    assert strategy.state["next_sell_price"] == 1.1198


def test_market_structure_hedge_grid_trails_tp_cancels_opposite_ca_and_grids_buy():
    strategy = MarketStructureHedgeGridStrategy(params={"symbol": "EURUSD"})
    strategy.on_init()
    strategy.state["buy_lot_used"] = 0.04
    strategy.state["next_buy_price"] = 1.1070
    strategy.state["buy_hedge_distance"] = 0.0030
    positions = [
        _buy_position(ticket=1, open_price=1.1000, current_price=1.1060),
        _buy_position(ticket=2, open_price=1.1040, current_price=1.1060),
    ]
    orders = [_pending_order(ticket=20, side="SELL", metadata={"comment": "CASell"})]

    context = _market_structure_context(positions=positions, orders=orders)
    actions = strategy.on_event(context)

    tp_actions = [action for action in actions if action.action_type == "MODIFY_TP"]
    assert {action.take_profit for action in tp_actions} == {1.102}
    assert any(
        action.action_type == "CANCEL_ORDER" and action.ticket == 20
        for action in actions
    )
    assert any(
        action.action_type == "OPEN" and action.reason == "GridBuy"
        for action in actions
    )


def test_market_structure_hedge_grid_is_registered():
    from services.simulation.strategy_registry import get_strategy_class

    assert (
        get_strategy_class("MarketStructureHedgeGridStrategy")
        is MarketStructureHedgeGridStrategy
    )

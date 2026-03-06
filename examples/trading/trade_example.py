"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys
import time
from datetime import datetime
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.utils.logger import logger
from apps.trading import Engine, core, Trade
from apps.utils.data_manipulator import TicksGenerator
from data.strategies.trend_following import TrendFollowingStrategy


# Global Variables
test_symbol = "NZDCAD"
audusd = "AUDUSD"
eurgbp = "EURGBP"
usdjpy = "USDJPY"
timeframe = "H1"
warmup_start_date = datetime(2024, 10, 1)  # 3 months of warmup data
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 31)
stoploss = 10

# Derived globals
backend = "sim"  # set to: "mt5" or "sim"
engine_instance = Engine(backend=backend)
api = engine_instance.api
account = api.account_info()

if backend == "sim":
    # Override selected MT5-derived fields for tester backend.
    account['login'] = 123456
    account['server'] = "Backtest Simulation Server"
    account['company'] = "HaruQuant"
    account['balance'] = 10000.0
    account['credit'] = 0.0
    account['profit'] = 0.0
    account['equity'] = 10000.0
    account['margin'] = 0.0
    account['margin_free'] = 10000.0

    mt5_test_symbol_info = engine_instance.client.symbol_info(test_symbol)
    mt5_audusd_symbol_info = engine_instance.client.symbol_info(audusd)
    mt5_eurgbp_symbol_info = engine_instance.client.symbol_info(eurgbp)
    mt5_usdjpy_symbol_info = engine_instance.client.symbol_info(usdjpy)
    engine_instance.state.trading_symbols.append(mt5_test_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_audusd_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_eurgbp_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_usdjpy_symbol_info)
    print("Using: Tester backend")

else:
    print("Using: MT5 backend")


trade = Trade(api)
trade.SetExpertMagicNumber(12345)
trade.SetDeviationInPoints(20)
trade.SetTypeFillingBySymbol(test_symbol)
pending_orders_created = []

def print_example_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def example_01_open_position():
    print_example_header("Example 01: Open Position")
    test_symbol_info = api.symbol_info(test_symbol)
    order_type = "BUY"
    point = float(test_symbol_info.point)
    open_price = float(test_symbol_info.bid) if order_type == "SELL" else float(test_symbol_info.ask)
    sl = open_price + (stoploss * point * 10) if order_type == "SELL" else open_price - (stoploss * point * 10)

    result = trade.PositionOpen(
            symbol=test_symbol,
            order_type=order_type,
            volume=0.01,
            price=open_price,
            sl=sl,
            tp=0.0,
            comment="Example open position",
        )
    if int(result.retcode) == 10009:
        print(f"{test_symbol} Position opened successfully with ticket {int(result.order)}")
    else:
        desc = str(trade.ResultRetcodeDescription())
        suffix = f"; {desc}" if desc and desc != str(int(result.retcode)) else ""
        print(
            f"{test_symbol} Position opening failed with retcode "
            f"retcode {int(result.retcode)}, {suffix}"
        )


def example_02_calculate_profit_margin():
    print_example_header("Example 02: Calculate Profit and Margin")
    volume = 0.10
    symbols_to_test = [audusd, usdjpy, eurgbp, test_symbol]
    ordered_symbols = []
    seen = set()
    for sym in symbols_to_test:
        if sym not in seen:
            seen.add(sym)
            ordered_symbols.append(sym)

    for sym in ordered_symbols:
        info = api.symbol_info(sym)
        if info is None:
            print(f"{sym}: symbol info unavailable, skipped")
            continue

        entry_price = float(info.ask)
        exit_price = entry_price + (265 * float(info.point))
        mt5_profit = engine_instance.client.order_calc_profit(0, sym, volume, entry_price, exit_price)
        mt5_margin = engine_instance.client.order_calc_margin(0, sym, volume, entry_price)

        # if backend == "tester":
        #     symbol_store = core.SymbolInfo(_account)
        #     symbol_store.AddSymbol(info)
        #     tester_profit = _simulator.order_calc_profit(0, sym, volume, entry_price, exit_price)
        #     tester_margin = _simulator.order_calc_margin(0, sym, volume, entry_price)
        #     print(f"{sym}: MT5=${mt5_profit} | Tester=${tester_profit}")
        # else:
        #     print(f"{sym}: MT5=${mt5_profit}")

        print(f"{sym}: MT5 profit = {mt5_profit}, margin = {mt5_margin}")


def example_03_modify_position():
    print_example_header("Example 03: Modify Position (SL/TP)")
    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    point = float(info.point)
    bid = float(info.bid)
    ask = float(info.ask)
    new_sl = bid - (30 * point * 10)
    new_tp = ask + (30 * point * 10)

    if backend == "mt5":
        result = trade.PositionModify(symbol=test_symbol, sl=new_sl, tp=new_tp)
        if result and int(result.retcode) in (10008, 10009):
            print(f"{test_symbol} Position modified successfully")
        else:
            print(
                f"{test_symbol} Position modify failed with retcode "
                f"{int(result.retcode)}"
            )
    else:
        ok = trade.PositionModify(symbol=test_symbol, sl=new_sl, tp=new_tp)
        retcode = int(trade.ResultRetcode())
        if ok and retcode == 10009:
            print(f"{test_symbol} Position modified successfully")
        else:
            desc = str(trade.ResultRetcodeDescription())
            suffix = f"; {desc}" if desc and desc != str(retcode) else ""
            print(
                f"{test_symbol} Position modify failed with retcode "
                f"{retcode}{suffix}"
            )


def example_04_close_partial_position():
    print_example_header("Example 04: Close Partial Position")
    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    open_price = float(info.ask)
    open_result = trade.PositionOpen(
        symbol=test_symbol,
        order_type="BUY",
        volume=0.02,
        price=open_price,
        sl=0.0,
        tp=0.0,
        comment="Example partial close seed",
    )

    if not open_result or int(open_result.retcode) not in (10008, 10009):
        print(f"{test_symbol}: seed position failed, partial close skipped")
        return

    result = trade.PositionClosePartial(symbol=test_symbol, volume=0.01)
    if result and int(result.retcode) in (10008, 10009):
        print(f"{test_symbol} Position partially closed successfully")
    else:
        print(
            f"{test_symbol} Partial close failed with retcode "
            f"{int(result.retcode)}"
        )


def example_05_close_position():
    print_example_header("Example 05: Close Position")
    result = trade.PositionClose(symbol=test_symbol)
    if result and int(result.retcode) in (10008, 10009):
        print(f"{test_symbol} Position closed successfully")
    else:
        print(
            f"{test_symbol} Position close failed with retcode "
            f"{int(result.retcode)}"
        )


def example_06_pending_orders():
    print_example_header("Example 06: Pending Orders (4 Types)")
    pending_orders_created.clear()
    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    bid = float(info.bid)
    ask = float(info.ask)
    point = float(info.point)
    step = 25 * point * 10
    expiration = int(time.time()) + 3600
    volume = 0.01

    pending_specs = [
        ("BUY_LIMIT", ask - step),
        ("BUY_STOP", ask + step),
        ("SELL_LIMIT", bid + step),
        ("SELL_STOP", bid - step),
    ]

    for order_type, pending_price in pending_specs:
        result = trade.OrderOpen(
            symbol=test_symbol,
            order_type=order_type,
            volume=volume,
            price=pending_price,
            sl=0.0,
            tp=0.0,
            expiration=datetime.fromtimestamp(expiration),
            comment=f"Example {order_type}",
        )
        if result and int(result.retcode) in (10008, 10009):
            ticket = int(result.order)
            pending_orders_created.append((ticket, order_type))
            print(f"{order_type}: placed successfully (order={ticket})")
        else:
            print(f"{order_type}: failed retcode={int(result.retcode)}")


def example_07_modify_pending_orders():
    print_example_header("Example 07: Modify Pending Orders")
    if not pending_orders_created:
        print("No pending orders available to modify")
        return

    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    bid = float(info.bid)
    ask = float(info.ask)
    point = float(info.point)
    step = 30 * point * 10
    expiration = int(time.time()) + 7200

    for ticket, order_type in pending_orders_created:
        if order_type == "BUY_LIMIT":
            new_price = ask - step
        elif order_type == "BUY_STOP":
            new_price = ask + step
        elif order_type == "SELL_LIMIT":
            new_price = bid + step
        else:
            new_price = bid - step

        result = trade.OrderModify(
            ticket=ticket,
            price=new_price,
            sl=0.0,
            tp=0.0,
            expiration=datetime.fromtimestamp(expiration),
        )
        if result and int(result.retcode) in (10008, 10009):
            print(f"{order_type} ticket {ticket}: modified")
        else:
            print(f"{order_type} ticket {ticket}: modify failed retcode={int(result.retcode)}")


def example_08_delete_pending_orders():
    print_example_header("Example 08: Delete Pending Orders")
    if not pending_orders_created:
        print("No pending orders available to delete")
        return

    remaining = []
    for ticket, order_type in pending_orders_created:
        result = trade.OrderDelete(ticket=ticket)
        if result and int(result.retcode) in (10008, 10009):
            print(f"{order_type} ticket {ticket}: deleted")
        else:
            print(f"{order_type} ticket {ticket}: delete failed retcode={int(result.retcode)}")
            remaining.append((ticket, order_type))

    pending_orders_created.clear()
    pending_orders_created.extend(remaining)

def example_09_monitoring_functions():
    print_example_header("Example 09: Monitoring Functions")
    if backend == "mt5":
        engine_instance.monitor_pending_orders(verbose=True)
        engine_instance.monitor_positions(verbose=True)
        engine_instance.monitor_account(verbose=True)
        print(
            f"Live snapshot: open_positions={len(engine_instance.state.trading_deals)} "
            f"active_orders={len(engine_instance.state.trading_orders)}"
        )
        return

    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    point = float(info.point)
    ask = float(info.ask)
    bid = float(info.bid)
    step = max(point * 10, 0.0001)

    # 1) Seed one pending order that is valid at creation time.
    order_result = trade.OrderOpen(
        symbol=test_symbol,
        order_type="BUY_LIMIT",
        volume=0.01,
        price=ask - step,
        sl=0.0,
        tp=0.0,
        comment="Monitor pending -> trigger",
    )
    if not order_result or int(order_result.retcode) not in (10008, 10009):
        print("Failed to seed pending order for monitoring demo")
        return
    pending_ticket = int(order_result.order)
    print(f"Seeded pending order ticket={pending_ticket}")

    # 2) Move price through trigger level and monitor pending orders.
    info.ask = ask - (2 * step)
    info.bid = bid - (2 * step)
    engine_instance.monitor_pending_orders(verbose=True)
    print(
        f"After monitor_pending_orders: active_orders={api.orders_total()} "
        f"open_positions={api.positions_total()}"
    )

    # 3) Force a TP hit on any open BUY positions and monitor positions.
    for pos in list(engine_instance.state.trading_deals):
        if int(getattr(pos, "type", -1)) == 0:
            pos.tp = float(getattr(pos, "price_current", info.bid) or info.bid) - step
            pos.sl = 0.0
    engine_instance.monitor_positions(verbose=True)
    print(
        f"After monitor_positions: open_positions={api.positions_total()} "
        f"history_deals={len(engine_instance.state.trading_history_deals)}"
    )

    # 4) Recompute account aggregates.
    engine_instance.monitor_account(verbose=True)
    acct = api.account_info()
    print(
        "Account snapshot: "
        f"balance={float(acct.get('balance', 0.0)):.2f}, "
        f"profit={float(acct.get('profit', 0.0)):.2f}, "
        f"equity={float(acct.get('equity', 0.0)):.2f}, "
        f"margin={float(acct.get('margin', 0.0)):.2f}, "
        f"margin_free={float(acct.get('margin_free', 0.0)):.2f}, "
        f"margin_level={float(acct.get('margin_level', 0.0)):.2f}"
    )

def example_10_simple_backtest():
    print_example_header("Example 10: Simple Backtest")

    client = engine_instance.client

    # Step 1: Load Data
    logger.info("\nLoading historical data...")
    # Load data from warmup_start_date to properly initialize indicators
    data = client.get_bars(
        symbol=test_symbol,
        timeframe=timeframe,
        date_from=warmup_start_date,
        date_to=end_date
    )
        
    if data is None or data.empty:
        logger.error("No data retrieved.")
        return

    # Step 2: Setup and initialize strategy
    logger.info("\nSetting up strategy...")
    strategy = TrendFollowingStrategy(
                params={
                'symbol': test_symbol,
                'fast_period': 20,
                'slow_period': 50,
                'filter_period': 200
            }
        )
    strategy.on_init()
    
    # Step 3: Pre-calculate signals (Vectorized/Pandas approach used by Strategy class)
    data = strategy.on_bar(data)
    #print(data)

    # Step 4: Cut data to start from start_date
    data = data[data.index >= start_date]
    if data is None or data.empty:
        logger.error("No data available after start_date filter.")
        return

    # Keep comparison window small and identical across models.
    compare_bars = data.copy()

    # Step 5: Convert bars data to ticks dataframe (multiple models)
    logger.info("\nConverting bars to ticks...")
    symbol_info = engine_instance.client.symbol_info(test_symbol)
    point_value = float(getattr(symbol_info, "point", 0.00001) or 0.00001)
    compare_start = compare_bars.index.min().to_pydatetime()
    compare_end = (
        compare_bars.index.max() + pd.Timedelta(minutes=59, seconds=59)
    ).to_pydatetime()
    # m1_data = client.get_bars(
    #     symbol=test_symbol,
    #     timeframe="M1",
    #     date_from=compare_start,
    #     date_to=compare_end,
    # )
    # if m1_data is not None and not m1_data.empty:
    #     m1_data = m1_data[
    #         (m1_data.index >= compare_bars.index.min())
    #         & (m1_data.index <= compare_end)
    #     ]
    # else:
    #     m1_data = None

    # # Fetch real ticks over the exact same comparison window.
    # real_ticks_start = compare_start
    # real_ticks_end = compare_end
    # real_ticks = client.get_ticks(
    #     symbol=test_symbol,
    #     start=real_ticks_start,
    #     end=real_ticks_end,
    #     as_dataframe=True,
    # )
    # if real_ticks is not None and not real_ticks.empty:
    #     if "timestamp" in real_ticks.columns:
    #         real_ticks = real_ticks.set_index("timestamp")
    #     real_ticks.index = real_ticks.index.tz_localize(None) if getattr(real_ticks.index, "tz", None) is not None else real_ticks.index
    # else:
    #     real_ticks = None

    start_tick = time.time()

    tick_model = "timeframe_ticks" # "real_ticks", "synthetic_ticks", "timeframe_ticks", "m1_ticks"
    spread_model = "native_spread" # "native_spread", "fixed_spread", "variable_spread"

    ticks_generator = TicksGenerator(
        model=tick_model,
        trading_timeframe=timeframe,
        # m1_data=m1_data,
        # real_ticks=real_ticks,
        point_value=point_value,
        spread_model=spread_model,
    )
    ticks_data = ticks_generator.generate(compare_bars)
    if ticks_data is None or ticks_data.empty:
        print(f"{tick_model}: no ticks generated (skipped)")

    end_tick = time.time()
    print(f"{tick_model}: generated {len(ticks_data)} ticks in {end_tick - start_tick} seconds")

    # Step 6: Run backtest
    start_time = time.time()

    engine_instance.configure_run_schedule(
      positions_every=1,          # only if you must enforce SL/TP each tick
      pending_orders_every=1,     # only if pending trigger must be tick-accurate     # only if you must enforce SL/TP each tick
      account_every=4,            # every 4 ticks represent bar close (ex real and synthetic ticks)
      portfolio_every=4,          
      risk_every=4,               
  )


    processed = engine_instance.run(
        ticks_data,
        position_size=0.01,
        monitor_verbose=True,
    )
    end_time = time.time()
    print(f"{tick_model}: processed {processed} ticks in {end_time - start_time} seconds")

    #print(ticks_data)


    

if __name__ == "__main__":
    # example_01_open_position()
    # example_02_calculate_profit_margin()
    # example_03_modify_position()
    # example_04_close_partial_position()
    # example_05_close_position()
    # example_06_pending_orders()
    # example_07_modify_pending_orders()
    # example_08_delete_pending_orders()
    # example_09_monitoring_functions()
    example_10_simple_backtest()

    

    if 'engine_instance' in locals():
            print("\nShutting down MT5 connection...")
            engine_instance.client.shutdown()
            print("Disconnected.")



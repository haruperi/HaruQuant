"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys
import time
from datetime import datetime
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.common.logger import logger
from apps.trading import Engine, core, Trade
from apps.risk import CorrelationPreference, RiskLimits
from backend.services.market_data.data_manipulator import TicksGenerator
from backend.db.sqlite.database_operations import DatabaseManager
from backend.data.strategies.trend_following import TrendFollowingStrategy
from backend.data.strategies.close_breakout import CloseBreakoutStrategy


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
    account['commission'] = 7

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

def reset_sim_runtime_state(account_balance = 10000, commission = 7.0, leverage = 400):
    if backend != "sim":
        return
    account = engine_instance.account_info()
    account["balance"] = account_balance
    account["profit"] = 0.0
    account["equity"] = account_balance
    account["margin"] = 0.0
    account["margin_free"] = account_balance
    account["margin_level"] = 0.0
    account["commission"] = commission
    account["leverage"] = leverage
    engine_instance.state.trading_deals = []
    engine_instance.state.trading_history_deals = []
    engine_instance.state.trading_orders = []
    engine_instance.state.trading_history_orders = []
    engine_instance.clear_completed_trades()
    pending_orders_created.clear()

def print_trade_record_summary(records):
    print(f"completed_trades={len(records)}")
    for idx, record in enumerate(records, start=1):
        print(
            f"trade[{idx}] ticket={record.ticket} symbol={record.symbol} side={record.type} "
            f"size={record.size:.2f} pnl={record.profit_loss:.2f} mfe={record.mfe_usd:.2f} "
            f"mae={record.mae_usd:.2f} close_type={record.close_type} exit_reason={record.exit_reason}"
        )

def print_run_result_summary(run_result):
    print(f"processed_ticks={run_result.processed_ticks}")
    print(f"final_balance={run_result.final_balance:.2f}")
    print(f"final_equity={run_result.final_equity:.2f}")
    print(f"completed_trades={len(run_result.trades)}")
    print(f"equity_points={len(run_result.equity_curve)}")
    if run_result.trades:
        first = run_result.trades[0]
        last = run_result.trades[-1]
        print(
            f"first_trade=ticket:{first.ticket} side:{first.type} pnl:{first.profit_loss:.2f} "
            f"mfe:{first.mfe_usd:.2f} mae:{first.mae_usd:.2f}"
        )
        print(
            f"last_trade=ticket:{last.ticket} side:{last.type} pnl:{last.profit_loss:.2f} "
            f"mfe:{last.mfe_usd:.2f} mae:{last.mae_usd:.2f}"
        )

def print_portfolio_symbol_summary(records, symbols: list[str]):
    summary = {symbol: {"trades": 0, "pnl": 0.0} for symbol in symbols}
    for record in records:
        symbol_name = str(getattr(record, "symbol", "") or "")
        if symbol_name not in summary:
            summary[symbol_name] = {"trades": 0, "pnl": 0.0}
        summary[symbol_name]["trades"] += 1
        summary[symbol_name]["pnl"] += float(getattr(record, "profit_loss", 0.0) or 0.0)

    for symbol_name in symbols:
        row = summary.get(symbol_name, {"trades": 0, "pnl": 0.0})
        print(
            f"portfolio_summary[{symbol_name}] trades={int(row['trades'])} pnl={float(row['pnl']):.2f}"
        )

def save_engine_backtest_snapshot(
    alias: str,
    description: str,
    strategy_name: str,
    symbols: list[str],
    timeframes: list[str],
    start_dt,
    end_dt,
    config_hash: str,
):
    completed_trades = engine_instance.get_completed_trades()
    equity_curve = engine_instance.get_equity_curve()
    db = DatabaseManager()
    db.initialize_database()
    backtest_id = db.create_backtest_run(
        strategy_name=strategy_name,
        strategy_version="1.0.0",
        start_date=start_dt,
        end_date=end_dt,
        engine_type="sim",
        data_resolution="timeframe_ticks",
        config_hash=config_hash,
        symbols=symbols,
        timeframes=timeframes,
        initial_balance=10000.0,
        alias=alias,
        description=description,
    )
    db.save_backtest_trades(backtest_id, completed_trades)
    db.save_backtest_equity_curve(backtest_id, equity_curve)
    final_balance = float(engine_instance.account_info().get("balance", 0.0) or 0.0)
    db.update_backtest_status(backtest_id, "completed", final_balance=final_balance)
    print(
        f"saved_backtest_id={backtest_id} db_path={db.db_path} "
        f"saved_trades={len(completed_trades)} saved_equity_points={len(equity_curve)}"
    )
    return backtest_id

def get_mutable_sim_symbol(symbol_name: str):
    for idx, symbol_row in enumerate(engine_instance.state.trading_symbols):
        name = str(getattr(symbol_row, "name", "") or "")
        if name != symbol_name:
            continue
        if isinstance(symbol_row, core.SymbolInfo):
            return symbol_row
        mutable = core.SymbolInfo(engine_instance._to_dict(symbol_row))
        engine_instance.state.trading_symbols[idx] = mutable
        return mutable
    return None

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
    info = get_mutable_sim_symbol(test_symbol)
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
        show_progress=True,
        progress_desc="Tester Progress",
    )
    end_time = time.time()



    # Trade Results Report and Save To DB
    run_result = engine_instance.get_run_result(processed_ticks=processed)
    print(f"Backtest completed in {end_time - start_time :.2f} seconds")
    print_run_result_summary(run_result)
    completed_trades = engine_instance.get_completed_trades()
    equity_curve = engine_instance.get_equity_curve()

    db = DatabaseManager()
    db.initialize_database()
    backtest_id = db.create_backtest_run(
        strategy_name="TrendFollowingStrategy",
        strategy_version="1.0.0",
        start_date=data.index.min().to_pydatetime(),
        end_date=data.index.max().to_pydatetime(),
        engine_type="sim",
        data_resolution="timeframe_ticks",
        config_hash=str(hash(("example_10", test_symbol, timeframe, len(data)))),
        symbols=[test_symbol],
        timeframes=[timeframe],
        initial_balance=10000.0,
        alias="example_10_trade_results_report_save_to_db",
        description="Engine.run completed trades + equity save example",
    )
    db.save_backtest_trades(backtest_id, completed_trades)
    db.save_backtest_equity_curve(backtest_id, equity_curve)
    final_balance = float(engine_instance.account_info().get("balance", 0.0) or 0.0)
    db.update_backtest_status(backtest_id, "completed", final_balance=final_balance)

    print(
        f"saved_backtest_id={backtest_id} db_path={db.db_path} "
        f"saved_trades={len(completed_trades)} saved_equity_points={len(equity_curve)}"
    )

    #print(ticks_data)
    # run_result_dict = run_result.to_dict()
    # print(run_result_dict)

def example_11_simple_backtest_pending():
    print_example_header("Example 11: Simple Backtest Pending")

    client = engine_instance.client

    logger.info("Loading historical data...")
    data = client.get_bars(
        symbol=test_symbol,
        timeframe=timeframe,
        date_from=warmup_start_date,
        date_to=end_date
    )

    if data is None or data.empty:
        logger.error("No data retrieved.")
        return

    logger.info("Setting up strategy...")
    strategy = CloseBreakoutStrategy(
        params={
            'symbol': test_symbol,
            'timeframe': timeframe,
        }
    )
    strategy.on_init()

    data = strategy.on_bar(data)
    data = data[data.index >= start_date]
    if data is None or data.empty:
        logger.error("No data available after start_date filter.")
        return

    compare_bars = data.head(40).copy()

    logger.info("Converting bars to ticks...")
    symbol_info = engine_instance.client.symbol_info(test_symbol)
    point_value = float(getattr(symbol_info, "point", 0.00001) or 0.00001)

    start_tick = time.time()
    tick_model = "timeframe_ticks"
    spread_model = "native_spread"

    ticks_generator = TicksGenerator(
        model=tick_model,
        trading_timeframe=timeframe,
        point_value=point_value,
        spread_model=spread_model,
    )
    ticks_data = ticks_generator.generate(compare_bars)
    if ticks_data is None or ticks_data.empty:
        print(f"{tick_model}: no ticks generated (skipped)")
        return

    end_tick = time.time()
    print(f"{tick_model}: generated {len(ticks_data)} ticks in {end_tick - start_tick} seconds")

    start_time = time.time()
    engine_instance.configure_run_schedule(
        positions_every=1,
        pending_orders_every=1,
        account_every=250,
        portfolio_every=250,
        risk_every=250,
    )

    processed = engine_instance.run(
        ticks_data,
        position_size=0.01,
        monitor_verbose=True,
        show_progress=True,
        progress_desc="Tester Progress",
    )
    end_time = time.time()
    print(f"{tick_model}: processed {processed} ticks in {end_time - start_time} seconds")

    print(
        "Pending demo summary: "
        f"active_orders={api.orders_total()} "
        f"open_positions={api.positions_total()} "
        f"history_orders={len(engine_instance.state.trading_history_orders)} "
        f"history_deals={len(engine_instance.state.trading_history_deals)}"
    )

def example_12_trade_results_partial_close():
    print_example_header("Example 12: Trade Results Partial Close")
    if backend != "sim":
        print("Example 12 is simulator-only")
        return

    reset_sim_runtime_state()

    info = get_mutable_sim_symbol(test_symbol)
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
        comment="Example 12 partial close seed",
    )
    if not open_result or int(open_result.retcode) not in (10008, 10009):
        print("Failed to open seed position")
        return

    point = float(info.point)
    info.bid = float(info.bid) + (150 * point * 10)
    info.ask = float(info.ask) + (150 * point * 10)
    engine_instance.monitor_positions(verbose=True)
    engine_instance.monitor_account(verbose=True)

    partial_result = trade.PositionClosePartial(symbol=test_symbol, volume=0.01)
    if not partial_result or int(partial_result.retcode) not in (10008, 10009):
        print("Partial close failed")
        return

    info.bid = float(info.bid) + (100 * point * 10)
    info.ask = float(info.ask) + (100 * point * 10)
    engine_instance.monitor_positions(verbose=True)
    engine_instance.monitor_account(verbose=True)

    close_result = trade.PositionClose(symbol=test_symbol)
    if not close_result or int(close_result.retcode) not in (10008, 10009):
        print("Final close failed")
        return

    records = engine_instance.get_completed_trades()
    print_trade_record_summary(records)
    print(f"equity_points={len(engine_instance.get_equity_curve())}")

def build_symbol_ticks_for_backtest(
    symbol_name: str,
    strategy_cls=TrendFollowingStrategy,
    tick_model: str = "timeframe_ticks",
    spread_model: str = "native_spread",
    return_signal_bars: bool = False,
):
    client = engine_instance.client
    data = client.get_bars(
        symbol=symbol_name,
        timeframe=timeframe,
        date_from=warmup_start_date,
        date_to=end_date,
    )
    if data is None or data.empty:
        logger.error(f"No data retrieved for {symbol_name}.")
        return None

    strategy = strategy_cls(
        params={
            "symbol": symbol_name,
            "fast_period": 20,
            "slow_period": 50,
            "filter_period": 200,
        }
    )
    strategy.on_init()
    data = strategy.on_bar(data)
    data = data[data.index >= start_date]
    if data is None or data.empty:
        logger.error(f"No signal-ready data available for {symbol_name} after start_date filter.")
        return None

    symbol_info = engine_instance.client.symbol_info(symbol_name)
    point_value = float(getattr(symbol_info, "point", 0.00001) or 0.00001)
    ticks_generator = TicksGenerator(
        model=tick_model,
        trading_timeframe=timeframe,
        point_value=point_value,
        spread_model=spread_model,
    )
    ticks_data = ticks_generator.generate(data.copy())
    if ticks_data is None or ticks_data.empty:
        logger.error(f"No ticks generated for {symbol_name}.")
        return None

    ticks_data = ticks_data.copy()
    ticks_data["symbol"] = symbol_name
    ticks_data["signal_timeframe"] = timeframe
    if return_signal_bars:
        return ticks_data, data.copy()
    return ticks_data


def example_13_simple_portfolion_backtest():
    print_example_header("Example 13: Simple Portfolion Backtest")

    if backend == "sim":
        reset_sim_runtime_state()

    portfolio_symbols = [test_symbol, audusd, eurgbp]
    tick_model = "timeframe_ticks"
    spread_model = "native_spread"
    merged_ticks = []
    per_symbol_counts = {}
    generation_started = time.time()

    logger.info("Loading and preparing portfolio symbol data...")
    for symbol_name in portfolio_symbols:
        symbol_started = time.time()
        ticks_data = build_symbol_ticks_for_backtest(
            symbol_name,
            tick_model=tick_model,
            spread_model=spread_model,
        )
        if ticks_data is None or ticks_data.empty:
            continue
        merged_ticks.append(ticks_data)
        per_symbol_counts[symbol_name] = len(ticks_data)
        print(
            f"portfolio {tick_model}: generated {len(ticks_data)} ticks for {symbol_name} "
            f"in {time.time() - symbol_started} seconds"
        )

    if not merged_ticks:
        print(f"portfolio {tick_model}: no ticks generated")
        return

    ticks_data = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
    print(
        f"portfolio {tick_model}: merged {len(ticks_data)} ticks across {len(per_symbol_counts)} symbols "
        f"in {time.time() - generation_started} seconds"
    )

    engine_instance.configure_run_schedule(
        positions_every=1,
        pending_orders_every=1,
        account_every=4,
        portfolio_every=4,
        risk_every=4,
    )

    start_time = time.time()
    processed = engine_instance.run(
        ticks_data,
        position_size=0.01,
        monitor_verbose=False,
        show_progress=True,
        progress_desc="Portfolio Tester Progress",
    )
    end_time = time.time()

    run_result = engine_instance.get_run_result(processed_ticks=processed)
    print(f"portfolio {tick_model}: processed {processed} ticks in {end_time - start_time} seconds")
    for symbol_name, count in per_symbol_counts.items():
        print(f"symbol_ticks[{symbol_name}]={count}")

    trade_counts = {}
    for record in run_result.trades:
        trade_counts[record.symbol] = trade_counts.get(record.symbol, 0) + 1

    print_run_result_summary(run_result)
    print_portfolio_symbol_summary(run_result.trades, portfolio_symbols)
    for symbol_name in portfolio_symbols:
        print(f"completed_trades[{symbol_name}]={trade_counts.get(symbol_name, 0)}")

    save_engine_backtest_snapshot(
        alias="example_13_simple_portfolion_backtest_save_to_db",
        description="Merged multi-symbol portfolio backtest using one shared engine run.",
        strategy_name="TrendFollowingStrategy",
        symbols=portfolio_symbols,
        timeframes=[timeframe],
        start_dt=ticks_data.index.min().to_pydatetime(),
        end_dt=ticks_data.index.max().to_pydatetime(),
        config_hash=str(hash(("example_13_portfolio", tuple(portfolio_symbols), timeframe, len(ticks_data)))),
    )


def example_14_portfolio_backtest_with_risk():
    print_example_header("Example 14: Portfolio Backtest With Risk")

    if backend == "sim":
        reset_sim_runtime_state()

    portfolio_symbols = [test_symbol, audusd, eurgbp]
    tick_model = "timeframe_ticks"
    spread_model = "native_spread"
    governor_timeframe = timeframe
    merged_ticks = []
    historical_data = {}
    per_symbol_counts = {}
    generation_started = time.time()

    logger.info("Loading and preparing portfolio symbol data for risk-managed run...")
    for symbol_name in portfolio_symbols:
        symbol_started = time.time()
        built = build_symbol_ticks_for_backtest(
            symbol_name,
            tick_model=tick_model,
            spread_model=spread_model,
            return_signal_bars=True,
        )
        if not built:
            continue
        ticks_data, signal_bars = built
        if ticks_data is None or ticks_data.empty:
            continue
        merged_ticks.append(ticks_data)
        historical_data[symbol_name] = {
            timeframe: signal_bars.copy(),
            governor_timeframe: signal_bars.copy(),
        }
        per_symbol_counts[symbol_name] = len(ticks_data)
        print(
            f"risk portfolio {tick_model}: generated {len(ticks_data)} ticks for {symbol_name} "
            f"in {time.time() - symbol_started} seconds"
        )

    if not merged_ticks:
        print(f"risk portfolio {tick_model}: no ticks generated")
        return

    ticks_data = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
    print(
        f"risk portfolio {tick_model}: merged {len(ticks_data)} ticks across {len(per_symbol_counts)} symbols "
        f"in {time.time() - generation_started} seconds"
    )

    engine_instance.configure_run_schedule(
        positions_every=1,
        pending_orders_every=1,
        account_every=4,
        portfolio_every=4,
        risk_every=4,
    )
    engine_instance.configure_risk_management(
        enabled=True,
        historical_data=historical_data,
        position_sizing_method="fixed_lot",
        position_sizing_config={
            "lot_size": 0.01,
        },
        risk_limits=RiskLimits(
            var_cap_frac=0.10,
            es_cap_frac=0.15,
            delta_var_cap_frac=0.03,
            delta_es_cap_frac=0.04,
            max_margin_used_frac=0.50,
            max_single_rc_frac=0.60,
            cluster_var_caps={"FOREX": 0.10},
            cluster_es_caps={"FOREX": 0.15},
        ),
        governor_timeframe=governor_timeframe,
        governor_start_pos=0,
        governor_end_pos=500,
        enable_regime_detection=True,
        regime_config={
            "lookback": 40,
            "vol_med_window": 10,
            "dd_trigger_frac": 0.05,
        },
        enable_allocation=True,
        correlation_preference=CorrelationPreference(
            target_corr=0.50,
            penalty_strength=2.0,
            min_budget_frac=0.30,
        ),
        risk_budgets={symbol_name: 1.0 / len(portfolio_symbols) for symbol_name in portfolio_symbols},
        symbol_clusters={symbol_name: "FOREX" for symbol_name in portfolio_symbols},
    )

    start_time = time.time()
    processed = engine_instance.run(
        ticks_data,
        position_size=0.01,
        monitor_verbose=True,
        show_progress=True,
        progress_desc="Risk Portfolio Tester Progress",
    )
    end_time = time.time()

    run_result = engine_instance.get_run_result(processed_ticks=processed)
    print(f"risk portfolio {tick_model}: processed {processed} ticks in {end_time - start_time} seconds")
    for symbol_name, count in per_symbol_counts.items():
        print(f"risk_symbol_ticks[{symbol_name}]={count}")

    trade_counts = {}
    for record in run_result.trades:
        trade_counts[record.symbol] = trade_counts.get(record.symbol, 0) + 1

    print_run_result_summary(run_result)
    print_portfolio_symbol_summary(run_result.trades, portfolio_symbols)
    for symbol_name in portfolio_symbols:
        print(f"risk_completed_trades[{symbol_name}]={trade_counts.get(symbol_name, 0)}")

    save_engine_backtest_snapshot(
        alias="example_14_portfolio_backtest_with_risk_save_to_db",
        description="Merged multi-symbol portfolio backtest using simulator risk management.",
        strategy_name="TrendFollowingStrategy",
        symbols=portfolio_symbols,
        timeframes=[timeframe],
        start_dt=ticks_data.index.min().to_pydatetime(),
        end_dt=ticks_data.index.max().to_pydatetime(),
        config_hash=str(hash(("example_14_portfolio_risk", tuple(portfolio_symbols), timeframe, len(ticks_data)))),
    )
    engine_instance.configure_risk_management(enabled=False)

def example_15_complete_backtests():
    print_example_header("Example 15: Complete Backtests")
    """
    This example is a pre-cursor to the UI, everything that will be done in
    this example is what will be done in the UI. And more attention given to 
    the inputs to match here and in the UI
    """

    # UI Inputs in order from top to bottom
    # Strategy & Data
    # Select the strategy and historical data parameters.

    # 1. Pick a strategy with its set defaults
    strategy = TrendFollowingStrategy

    # 2. Pick a trading timeframe
    trading_timeframe = timeframe

    # 3. Pick a symbol or symbols
    symbols = [test_symbol, audusd, eurgbp]

    # 4. Pick a data source Metatrader5 or Dukascopy API
    data_source = "metatrader"

    # 5. Money Management
    position_size_type = "fixed_lot" # fixed_lot, fixed_percent, milestone, kelly_criterion, volatility_adjusted_atr, fixed_fractional
    position_size_config = None
    if position_size_type == "fixed_lot":
        position_size_config = {
            "lot_size": 0.1
        }
    elif position_size_type == "fixed_percent":
        position_size_config = {
            "risk_percent": 1.0,
            "use_dynamic_stop_loss": False
        }
    elif position_size_type == "milestone":
        position_size_config = {
            "initial_balance": 1000.0,
            "base_lot_size": 0.1,
            "milestone_amount": 3000.0,
            "lot_increment": 0.1,
        }
    elif position_size_type == "kelly_criterion":
        position_size_config = {
            "kelly_fraction_limit": 0.25,
            "win_rate": 0.55,
            "avg_win": 150.0,
            "avg_loss": 100.0,
        }
    elif position_size_type == "volatility_adjusted_atr":
        position_size_config = {
            "risk_percent": 1.0,
            "atr_multiplier": 2.0,
        }
    elif position_size_type == "fixed_fractional":
        position_size_config = {
            "fractional_factor": 0.5,
        }

    # 6. Pick Data Range
    range_by = "dates" # dates, bars
    if range_by == "dates":
        bt_start_date = start_date
        bt_end_date = end_date
    else:
        bars = 1000

    # 6. Pick Warmup Period
    warmup_by = "dates" # dates, bars
    if warmup_by == "dates":
        bt_warmup_start_date = warmup_start_date
    else:
        warmup_bars = 100

    # Engine Settings
    # Engine Type Event-Driven or Vectorised has been removed for now,
    # everything is event-driven via loop

    # 7. Data resolution
    tick_model = "timeframe_ticks" # "real_ticks", "synthetic_ticks", "timeframe_ticks", "m1_ticks"

    # 8. Account details
    account_balance = 10000 
    commission = 7.0
    leverage = 400
    if backend == "sim":
        reset_sim_runtime_state(account_balance, commission, leverage)

    # 9. Trading Conditions
    slippage_config = None
    slippage_model = "fixed" # fixed, dynamic
    if slippage_model == "fixed":
        slippage_config = {
            "slippage_points": 1 
        }
    elif slippage_model == "dynamic":
        slippage_config = {
            "slippage_min": 1, 
            "slippage_max": 10
        }

    spread_config = None
    spread_model = "native_spread" # native_spread, fixed, dynamic
    if spread_model == "fixed":
        spread_config = {
            "spread_points": 10 
        }
    elif spread_model == "dynamic":
        spread_config = {
            "spread_min": 10, 
            "spread_max": 50
        }
    
    
    # Preparing data for backtest
    # Step 1: Load Data
    logger.info("\nLoading historical data...")
    # Load data from warmup_start_date to properly initialize indicators
    merged_ticks = []
    per_symbol_counts = {}

    logger.info("Loading and preparing portfolio symbol data...")
    for symbol in symbols:
        ticks_data = build_symbol_ticks_for_backtest(
            symbol,
            tick_model=tick_model,
            spread_model=spread_model,
        )
        if ticks_data is None or ticks_data.empty:
            continue
        merged_ticks.append(ticks_data)
        per_symbol_counts[symbol] = len(ticks_data)

    if not merged_ticks:
        print(f"No ticks generated")
        return

    ticks_data = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
    print(f"merged {len(ticks_data)} ticks across {len(per_symbol_counts)} symbols")

    engine_instance.configure_run_schedule(
        positions_every=1,
        pending_orders_every=1,
        account_every=4,
        portfolio_every=4,
        risk_every=4,
    )

    processed = engine_instance.run(
        ticks_data,
        position_size=0.01,
        monitor_verbose=False,
        show_progress=True,
        progress_desc="Portfolio Tester Progress",
    )

    run_result = engine_instance.get_run_result(processed_ticks=processed)
    for symbol_name, count in per_symbol_counts.items():
        print(f"symbol_ticks[{symbol_name}]={count}")

    trade_counts = {}
    for record in run_result.trades:
        trade_counts[record.symbol] = trade_counts.get(record.symbol, 0) + 1

    print_run_result_summary(run_result)
    print_portfolio_symbol_summary(run_result.trades, symbols)
    for symbol_name in symbols:
        print(f"completed_trades[{symbol_name}]={trade_counts.get(symbol_name, 0)}")





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
    # example_10_simple_backtest()
    # example_11_simple_backtest_pending()
    # example_12_trade_results_partial_close()
    # example_13_simple_portfolion_backtest()
    # example_14_portfolio_backtest_with_risk()
    example_15_complete_backtests()
 

    

    if 'engine_instance' in locals():
            print("\nShutting down MT5 connection...")
            engine_instance.client.shutdown()
            print("Disconnected.")












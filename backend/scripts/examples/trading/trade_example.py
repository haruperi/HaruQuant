"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys
import time
from datetime import datetime
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.common.logger import logger
from backend.services.simulation.config import AccountConfig
from backend.services.simulation.engine import Engine
from backend.services.simulation.reporting import print_simulation_summary
from backend.services.execution import core
from backend.services.execution.trade import Trade
from backend.services.risk_engine import CorrelationPreference, RiskLimits
from backend.services.market_data.data_manipulator import TicksGenerator
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.data.strategies.trend_following import TrendFollowingStrategy
from backend.data.strategies.close_breakout import CloseBreakoutStrategy


# Global Variables
test_symbol = "GBPUSD"
audusd = "AUDUSD"
eurgbp = "EURGBP"
nzdchf = "NZDCHF"
timeframe = "H1"
warmup_start_date = datetime(2014, 12, 1)  # 3 months of warmup data
start_date = datetime(2015, 1, 1)
end_date = datetime(2025, 12, 31)
stoploss = 10

# Derived globals``
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
    mt5_nzdchf_symbol_info = engine_instance.client.symbol_info(nzdchf)
    engine_instance.state.trading_symbols.append(mt5_test_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_audusd_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_eurgbp_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_nzdchf_symbol_info)
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
    engine_instance.reset_runtime(
        AccountConfig(
            initial_balance=float(account_balance),
            commission=float(commission),
            leverage=int(leverage),
            currency=str(engine_instance.account_info().get("currency", "USD") or "USD"),
        )
    )
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
    symbols_to_test = [audusd, nzdchf, eurgbp, test_symbol]
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
    trade.PositionClose(symbol=test_symbol)
    print_example_header("Example 04: Close Partial Position")
    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    open_price = float(info.ask)
    open_result = trade.PositionOpen(
        symbol=test_symbol,
        order_type="BUY",
        volume=0.04,
        price=open_price,
        sl=0.0,
        tp=0.0,
        comment="Example partial close seed",
    )

    time.sleep(2)

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

    info = get_mutable_sim_symbol(test_symbol)
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

def example_12_complete_backtests():
    print_example_header("Example 12: Complete Backtests")
    started = time.time()
    config = {
        "engine_type": "event_driven",
        "account": {
            "initial_balance": 10000.0,
            "commission": 7.0,
            "leverage": 400,
            "currency": "USD",
        },
        "data": {
            "source": "metatrader",
            "symbols": [test_symbol],
            "timeframe": "H1",
            "start": start_date,
            "end": end_date,
            "warmup_start": warmup_start_date,
        },
        "strategy": {
            "name": "TrendFollowingStrategy",
            "params": {
                "fast_period": 20,
                "slow_period": 50,
                "filter_period": 200,
            },
        },
        "execution": {
            "tick_model": "timeframe_ticks",
            "spread_model": "native_spread",
            "slippage_model": "fixed",
            "slippage_points": 1,
            "contract_size": 100000,
            "position_size": {
                "type": "fixed_lot",
                "lot_size": 0.1,
            },
        },
        "reporting": {
            "print_summary": False,
            "save_to_db": False,
            "alias": "example_12_complete_backtests",
            "description": "Clean config-driven portfolio simulation example.",
            "equity_snapshot_policy": "position_update",
        },
    }

    result = engine_instance.run(config)
    print_simulation_summary(result)

    #print([point.to_dict() for point in result.run_result.equity_curve])

    '''
    Its structure is:

        SimulationRunResult(
            config=SimulationConfig(...),
            prepared=PreparedSimulationData(...),
            run_result=RunResult(...),
            metrics={...},
            symbol_summary={...},
            warnings=(),
            metadata={...},
        )

        The most useful fields on result are:

        - result.config
            The parsed simulation config object.
        - result.prepared
            The prepared market data bundle used for the run.
        - result.run_result
            The low-level packaged engine result:

            RunResult(
                trades=[TradeRecord, ...],
                equity_curve=[EquityPoint, ...],
                processed_ticks=int,
                final_balance=float,
                final_equity=float
            )
        - result.metrics
            A flat summary dict like:

            {
                "processed_ticks": ...,
                "trade_count": ...,
                "equity_points": ...,
                "initial_balance": ...,
                "final_balance": ...,
                "final_equity": ...,
                "total_profit": ...,
                "total_return": ...
            }
        - result.symbol_summary
            Per-symbol pnl/trade summary:

            {
                "AUDUSD": {"trades": 12.0, "pnl": 153.2},
                "EURGBP": {"trades": 8.0, "pnl": -41.0},
                "NZDCHF": {"trades": 5.0, "pnl": 22.5}
            }
        - result.metadata
            Run metadata such as engine type, symbols, timeframe, tick model, processed ticks, and prepared-data metadata.
    '''


    


    print(f"total_seconds={time.time() - started:.4f}")


def example_13_simple_portfolion_backtest():
    print_example_header("Example 13: Simple Portfolio Backtest")
    started = time.time()
    config = {
        "engine_type": "event_driven",
        "account": {
            "initial_balance": 10000.0,
            "commission": 7.0,
            "leverage": 400,
        },
        "data": {
            "source": "metatrader",
            "symbols": [test_symbol, audusd, eurgbp],
            "timeframe": "H1",
            "start": start_date,
            "end": end_date,
            "warmup_start": warmup_start_date,
        },
        "strategy": {
            "name": "TrendFollowingStrategy",
            "params": {
                "fast_period": 20,
                "slow_period": 50,
                "filter_period": 200,
            },
        },
        "execution": {
            "tick_model": "timeframe_ticks",
            "spread_model": "native_spread",
            "contract_size": 100000,
            "position_size": {
                "type": "fixed_lot",
                "lot_size": 0.01,
            },
        },
        "reporting": {
            "print_summary": True,
            "save_to_db": True,
            "alias": "example_13_simple_portfolion_backtest",
            "description": "Event-driven multi-symbol portfolio backtest.",
        },
    }

    result = engine_instance.run(config)
    print_simulation_summary(result)
    print(f"total_seconds={time.time() - started:.4f}")


def example_14_portfolio_backtest_with_risk():
    print_example_header("Example 14: Portfolio Backtest With Risk")
    started = time.time()
    config = {
        "engine_type": "event_driven",
        "account": {
            "initial_balance": 10000.0,
            "commission": 7.0,
            "leverage": 400,
        },
        "data": {
            "source": "metatrader",
            "symbols": [test_symbol, audusd, eurgbp],
            "timeframe": "H1",
            "start": start_date,
            "end": end_date,
            "warmup_start": warmup_start_date,
        },
        "strategy": {
            "name": "TrendFollowingStrategy",
            "params": {
                "fast_period": 20,
                "slow_period": 50,
                "filter_period": 200,
            },
        },
        "execution": {
            "tick_model": "timeframe_ticks",
            "spread_model": "native_spread",
            "contract_size": 100000,
            "position_size": {
                "type": "fixed_lot",
                "lot_size": 0.01,
            },
        },
        "risk": {
            "enabled": True,
            "risk_limits": {
                "var_cap_frac": 0.10,
                "es_cap_frac": 0.15,
                "max_margin_used_frac": 0.50,
            },
            "enable_regime_detection": True,
            "enable_allocation": True,
            "correlation_preference": {
                "target_corr": 0.50,
                "penalty_strength": 2.0,
            },
        },
        "reporting": {
            "print_summary": True,
            "save_to_db": True,
            "alias": "example_14_portfolio_backtest_with_risk",
            "description": "Portfolio backtest with active risk management.",
        },
    }

    result = engine_instance.run(config)
    print_simulation_summary(result)
    print(f"total_seconds={time.time() - started:.4f}")




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
    example_12_complete_backtests()
    #example_13_simple_portfolion_backtest()
    #example_14_portfolio_backtest_with_risk()


  




 

  

 

    

    if 'engine_instance' in locals():
            print("\nShutting down MT5 connection...")
            engine_instance.client.shutdown()
            print("Disconnected.")












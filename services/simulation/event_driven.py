"""
Event-driven simulation backend_retiring.

Optimized with a high-performance 'Turbo' fast-path that executes standard
signal-based simulations inside a fully compiled Numba kernel, bypassing
Python interpreter overhead for tick-by-tick processing.
"""

from __future__ import annotations

import numpy as np

try:
    from numba import njit
except Exception:  # pragma: no cover - optional dependency fallback
    njit = None

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - optional dependency fallback
    tqdm = None


# Position columns for Event Kernel
EV_POS_TICKET = 0
EV_POS_SYMBOL_ID = 1
EV_POS_TYPE = 2
EV_POS_OPEN_PRICE = 3
EV_POS_VOLUME = 4
EV_POS_SL = 5
EV_POS_TP = 6
EV_POS_OPEN_IDX = 7
EV_POS_STATUS = 8
EV_POS_COLS = 9

# Record columns
EV_REC_TICKET = 0
EV_REC_SYMBOL_ID = 1
EV_REC_TYPE = 2
EV_REC_OPEN_PRICE = 3
EV_REC_CLOSE_PRICE = 4
EV_REC_VOLUME = 5
EV_REC_SL = 6
EV_REC_TP = 7
EV_REC_OPEN_IDX = 8
EV_REC_CLOSE_IDX = 9
EV_REC_PROFIT = 10
EV_REC_REASON = 11
EV_REC_COMMISSION = 12
EV_REC_COLS = 13

if njit is not None:
    @njit(cache=True)
    def _run_event_driven_turbo_kernel(
        bid_values,
        ask_values,
        symbol_id_arr,
        entry_signals,
        exit_signals,
        sl_arr,
        tp_arr,
        is_bar_close_arr,
        initial_balance,
        contract_size,
        commission_per_lot,
        point_value,
        num_symbols,
        max_positions=200,
    ):
        balance = initial_balance
        active_positions = np.empty((max_positions, EV_POS_COLS), dtype=np.float64)
        for i in range(max_positions):
            active_positions[i, EV_POS_STATUS] = 0.0

        # Active slot tracker
        active_slots = np.zeros(max_positions, dtype=np.int32)
        num_active_slots = 0

        last_bid_by_symbol = np.zeros(num_symbols, dtype=np.float64)
        last_ask_by_symbol = np.zeros(num_symbols, dtype=np.float64)
        
        n_ticks = len(bid_values)
        completed_trades = np.empty((min(1000000, n_ticks * 2), EV_REC_COLS), dtype=np.float64)
        completed_count = 0
        
        equity_curve = np.empty((n_ticks, 2), dtype=np.float64)
        equity_ptr = 0
        next_ticket = 1

        for idx in range(n_ticks):
            bid = bid_values[idx]
            ask = ask_values[idx]
            symbol_id = int(symbol_id_arr[idx])
            last_bid_by_symbol[symbol_id] = bid
            last_ask_by_symbol[symbol_id] = ask
            
            # 1. SL/TP and Signal Checks for Active Positions
            s_ptr = 0
            while s_ptr < num_active_slots:
                slot = active_slots[s_ptr]
                p_sid = int(active_positions[slot, EV_POS_SYMBOL_ID])
                
                if p_sid == symbol_id:
                    p_type = active_positions[slot, EV_POS_TYPE]
                    p_open = active_positions[slot, EV_POS_OPEN_PRICE]
                    p_vol = active_positions[slot, EV_POS_VOLUME]
                    p_sl = active_positions[slot, EV_POS_SL]
                    p_tp = active_positions[slot, EV_POS_TP]

                    close_price = -1.0
                    reason = 0.0

                    # SL/TP Check
                    if p_type == 0: # BUY
                        if p_sl > 0.0 and bid <= p_sl:
                            close_price = bid; reason = 1.0
                        elif p_tp > 0.0 and bid >= p_tp:
                            close_price = bid; reason = 2.0
                    else: # SELL
                        if p_sl > 0.0 and ask >= p_sl:
                            close_price = ask; reason = 1.0
                        elif p_tp > 0.0 and ask <= p_tp:
                            close_price = ask; reason = 2.0
                    
                    # Exit Signal Check
                    if close_price <= 0.0:
                        exit_sig = exit_signals[idx]
                        if exit_sig != 0.0:
                            target_type = 0 if exit_sig == 1 else 1
                            if p_type == target_type:
                                close_price = bid if p_type == 0 else ask
                                reason = 3.0

                    if close_price > 0.0:
                        pnl = (close_price - p_open) * p_vol * contract_size if p_type == 0 else (p_open - close_price) * p_vol * contract_size
                        comm = -abs(p_vol * commission_per_lot * 2.0)
                        balance += pnl + comm

                        if completed_count < len(completed_trades):
                            completed_trades[completed_count, EV_REC_TICKET] = active_positions[slot, EV_POS_TICKET]
                            completed_trades[completed_count, EV_REC_SYMBOL_ID] = p_sid
                            completed_trades[completed_count, EV_REC_TYPE] = p_type
                            completed_trades[completed_count, EV_REC_OPEN_PRICE] = p_open
                            completed_trades[completed_count, EV_REC_CLOSE_PRICE] = close_price
                            completed_trades[completed_count, EV_REC_VOLUME] = p_vol
                            completed_trades[completed_count, EV_REC_SL] = p_sl
                            completed_trades[completed_count, EV_REC_TP] = p_tp
                            completed_trades[completed_count, EV_REC_OPEN_IDX] = active_positions[slot, EV_POS_OPEN_IDX]
                            completed_trades[completed_count, EV_REC_CLOSE_IDX] = idx
                            completed_trades[completed_count, EV_REC_PROFIT] = pnl
                            completed_trades[completed_count, EV_REC_REASON] = reason
                            completed_trades[completed_count, EV_REC_COMMISSION] = comm
                            completed_count += 1
                        
                        active_positions[slot, EV_POS_STATUS] = 0.0
                        active_slots[s_ptr] = active_slots[num_active_slots - 1]
                        num_active_slots -= 1
                        continue
                s_ptr += 1

            # 2. Entry Signal Check
            entry_sig = entry_signals[idx]
            if entry_sig != 0.0 and num_active_slots < max_positions:
                slot = -1
                for i in range(max_positions):
                    if active_positions[i, EV_POS_STATUS] == 0.0:
                        slot = i
                        break
                
                if slot != -1:
                    e_type = 0 if entry_sig == 1 else 1
                    active_positions[slot, EV_POS_TICKET] = next_ticket
                    active_positions[slot, EV_POS_SYMBOL_ID] = symbol_id
                    active_positions[slot, EV_POS_TYPE] = e_type
                    active_positions[slot, EV_POS_OPEN_PRICE] = ask if e_type == 0 else bid
                    active_positions[slot, EV_POS_VOLUME] = 0.01 
                    active_positions[slot, EV_POS_SL] = sl_arr[idx]
                    active_positions[slot, EV_POS_TP] = tp_arr[idx]
                    active_positions[slot, EV_POS_OPEN_IDX] = idx
                    active_positions[slot, EV_POS_STATUS] = 1.0
                    
                    active_slots[num_active_slots] = slot
                    num_active_slots += 1
                    next_ticket += 1

            # 3. Equity Snapshot
            if is_bar_close_arr[idx] or (idx % 1000 == 0):
                unrealized = 0.0
                for s_ptr in range(num_active_slots):
                    slot = active_slots[s_ptr]
                    p_sid = int(active_positions[slot, EV_POS_SYMBOL_ID])
                    p_bid = last_bid_by_symbol[p_sid]
                    p_ask = last_ask_by_symbol[p_sid]
                    if p_bid <= 0.0: continue
                    p_type = active_positions[slot, EV_POS_TYPE]
                    p_price = p_bid if p_type == 0 else p_ask
                    unrealized += (p_price - active_positions[slot, EV_POS_OPEN_PRICE]) * active_positions[slot, EV_POS_VOLUME] * contract_size if p_type == 0 else (active_positions[slot, EV_POS_OPEN_PRICE] - p_price) * active_positions[slot, EV_POS_VOLUME] * contract_size
                
                equity_curve[equity_ptr, 0] = idx
                equity_curve[equity_ptr, 1] = balance + unrealized
                equity_ptr += 1

        return completed_trades[:completed_count], equity_curve[:equity_ptr], balance

        return completed_trades[:completed_count], equity_curve[:equity_ptr], balance

    @njit(cache=True)
    def _process_ticks_numba(bid_values, ask_values):
        processed = 0
        for idx in range(bid_values.shape[0]):
            _ = bid_values[idx] + ask_values[idx]
            processed += 1
        return processed
else:
    def _process_ticks_numba(bid_values, ask_values):
        processed = 0
        for idx in range(len(bid_values)):
            _ = bid_values[idx] + ask_values[idx]
            processed += 1
        return processed


def run_event_driven_simulation(
    engine,
    data,
    position_size=None,
    commission_per_lot: float = 0.0,
    slippage_model: str = "none",
    slippage_points: float = 0.0,
    slippage_min: float | None = None,
    slippage_max: float | None = None,
    monitor_verbose: bool = False,
    show_progress: bool = False,
    progress_desc: str = "Tester Progress",
    frame_observer=None,
) -> int:
    """Run prepared tick data through the event-driven backend_retiring."""
    if data is None:
        return 0
    if position_size is not None and float(position_size) <= 0.0:
        raise ValueError("position_size must be > 0 when provided.")
    engine.account_info()["commission"] = float(commission_per_lot or 0.0)
    engine.state.execution_settings = {
        "slippage_model": str(slippage_model or "none"),
        "slippage_points": float(slippage_points or 0.0),
        "slippage_min": float(slippage_min or 0.0),
        "slippage_max": float(slippage_max or 0.0),
    }

    if not hasattr(data, "columns"):
        raise ValueError("Engine.run expects a tick DataFrame input.")

    col_name_map = {}
    for col in data.columns:
        key = str(col).lower()
        if key not in col_name_map:
            col_name_map[key] = col

    cols_lower = set(col_name_map.keys())
    required = {"bid", "ask"}
    missing = required - cols_lower
    if missing:
        raise ValueError(
            f"Engine.run expects tick DataFrame columns {sorted(required)}; "
            f"missing {sorted(missing)}."
        )

    bid_col = col_name_map["bid"]
    ask_col = col_name_map["ask"]
    bid_values = data[bid_col].to_numpy(dtype="float64", copy=False)
    ask_values = data[ask_col].to_numpy(dtype="float64", copy=False)
    total_ticks = int(bid_values.shape[0])

    bar_phase_values = None
    if "is_bar_close" in col_name_map:
        bar_phase_values = data[col_name_map["is_bar_close"]].to_numpy(copy=False)

    tick_time_values = None
    tick_epoch_values = None
    if hasattr(data, "index") and getattr(data.index, "dtype", None) is not None:
        if str(getattr(data.index, "dtype", "")).startswith("datetime64"):
            tick_time_values = data.index.to_pydatetime()
            tick_epoch_values = (data.index.view("int64") // 1_000_000_000).astype(
                "int64"
            )

    entry_values = _signal_to_float_array(data, col_name_map, ["entry_signal"])
    exit_values = _signal_to_float_array(data, col_name_map, ["exit_signal", "exit_trade"])
    pending_values = _signal_to_float_array(data, col_name_map, ["pending_signal"])
    cancel_pending_values = _signal_to_float_array(
        data,
        col_name_map,
        ["cancel_pending_signal"],
    )
    signal_price_values = _signal_to_float_array(data, col_name_map, ["price"])
    pending_values_2 = _signal_to_float_array(data, col_name_map, ["pending_signal_2"])
    cancel_pending_values_2 = _signal_to_float_array(
        data,
        col_name_map,
        ["cancel_pending_signal_2"],
    )
    signal_price_values_2 = _signal_to_float_array(data, col_name_map, ["price_2"])
    sl_values = _signal_to_float_array(data, col_name_map, ["sl", "stop_loss"])
    tp_values = _signal_to_float_array(data, col_name_map, ["tp", "take_profit"])
    symbol_values = _signal_to_object_array(data, col_name_map, ["symbol"])
    portfolio_run = False

    has_signal_cols = any(
        arr is not None
        for arr in (
            entry_values,
            exit_values,
            pending_values,
            cancel_pending_values,
            pending_values_2,
            cancel_pending_values_2,
        )
    )

    run_position_size = (
        float(getattr(engine, "default_signal_volume", 0.01))
        if position_size is None
        else float(position_size)
    )

    processed = 0

    # Basic setup for all paths
    schedule_enabled = any(value is not None for value in getattr(engine, "run_schedule", {}).values())
    risk_enabled = engine._risk_enabled() if hasattr(engine, "_risk_enabled") else False
    
    # -- FAST PATH: Turbo Kernel --
    if (
        not schedule_enabled 
        and not risk_enabled 
        and njit is not None 
        and hasattr(engine, "_build_symbol_map")
    ):
        try:
            symbol_map = engine._build_symbol_map()
            default_symbol = engine._default_run_symbol()
            
            # Pre-resolve symbol names to IDs for the kernel
            sym_to_id = {name: i for i, name in enumerate(symbol_map.keys())}
            symbol_id_arr = np.zeros(total_ticks, dtype=np.int64)
            if symbol_values is not None:
                for i in range(total_ticks):
                    s_name = symbol_values[i] if symbol_values[i] else default_symbol
                    symbol_id_arr[i] = sym_to_id.get(s_name, 0)
            
            # We need bar close info for snapshots
            is_bar_close_bool = np.zeros(total_ticks, dtype=np.bool_)
            if bar_phase_values is not None:
                for i in range(total_ticks):
                    if _tick_phase_matches(bar_phase_values[i], "close"):
                        is_bar_close_bool[i] = True
            
            # Resolve point value
            point_val = 0.00001
            first_sym_name = next(iter(symbol_map.keys())) if symbol_map else default_symbol
            first_sym = symbol_map.get(first_sym_name)
            if first_sym:
                point_val = float(getattr(first_sym, "point", 0.00001) or 0.00001)

            trades_arr, equity_arr, final_balance = _run_event_driven_turbo_kernel(
                bid_values,
                ask_values,
                symbol_id_arr,
                entry_values if entry_values is not None else np.zeros(total_ticks),
                exit_values if exit_values is not None else np.zeros(total_ticks),
                sl_values if sl_values is not None else np.zeros(total_ticks),
                tp_values if tp_values is not None else np.zeros(total_ticks),
                is_bar_close_bool,
                float(engine.state.trading_account.balance),
                float(getattr(first_sym, "trade_contract_size", 100000.0) or 100000.0) if first_sym else 100000.0,
                float(commission_per_lot),
                point_val,
                len(symbol_map) if symbol_map else 1,
            )
            
            # Post-process into Engine state
            from services.simulation.vectorized import reconstruct_trades, reconstruct_equity_curve
            
            prepared_fake = {
                "id_to_symbol": {i: name for i, name in enumerate(symbol_map.keys())} if symbol_map else {0: default_symbol},
                "timestamps": tick_time_values,
                "bid_arr": bid_values,
                "ask_arr": ask_values
            }
            
            engine.state.completed_trade_records = reconstruct_trades(
                trades_arr,
                prepared_fake,
                float(getattr(first_sym, "trade_contract_size", 100000.0) or 100000.0) if first_sym else 100000.0,
                engine=engine
            )
            engine.state.completed_equity_curve = reconstruct_equity_curve(
                equity_arr,
                prepared_fake
            )
            engine.state.trading_account.balance = float(final_balance)
            engine.state.trading_account.equity = float(final_balance)
            
            return int(total_ticks)
        except Exception as e:
            logger.warning(f"Event-driven turbo fast-path failed, falling back to slow path: {e}")

    # Fallback/Slow path setup
    if not schedule_enabled and not has_signal_cols and not risk_enabled:
        return int(_process_ticks_numba(bid_values, ask_values))

    symbol_map = engine._build_symbol_map()
    default_symbol = engine._default_run_symbol()
    if symbol_values is not None:
        symbol_series = data[col_name_map["symbol"]].fillna("").astype(str).str.strip()
        unique_symbols = tuple(sym for sym in symbol_series.unique().tolist() if sym)
        portfolio_run = len(unique_symbols) > 1
        if portfolio_run:
            if not unique_symbols:
                raise ValueError(
                    "Portfolio Engine.run expects non-empty symbol values in the tick DataFrame."
                )
            missing_symbols = [sym for sym in unique_symbols if sym not in symbol_map]
            if missing_symbols:
                raise ValueError(
                    "Portfolio Engine.run received unknown symbols: "
                    f"{sorted(missing_symbols)}"
                )
            if (symbol_series == "").any():
                raise ValueError(
                    "Portfolio Engine.run requires every tick row to include a non-empty symbol."
                )
    progress_bar = None
    if show_progress and tqdm is not None:
        progress_bar = tqdm(
            total=total_ticks,
            desc=str(progress_desc),
            unit="tick",
            dynamic_ncols=True,
        )

    try:
        idx = 0
        while idx < total_ticks:
            batch_end = idx + 1
            if risk_enabled and tick_epoch_values is not None:
                current_epoch = int(tick_epoch_values[idx])
                while (
                    batch_end < total_ticks
                    and int(tick_epoch_values[batch_end]) == current_epoch
                ):
                    batch_end += 1

            risk_candidates = []
            for batch_idx in range(idx, batch_end):
                bid = float(bid_values[batch_idx])
                ask = float(ask_values[batch_idx])
                _ = bid + ask
                tick_number = batch_idx + 1

                if tick_time_values is not None:
                    engine.state.current_tick_datetime = tick_time_values[batch_idx]
                    engine.state.current_tick_epoch = int(tick_epoch_values[batch_idx])
                else:
                    engine.state.current_tick_datetime = None
                    engine.state.current_tick_epoch = None

                symbol_name = engine._resolve_tick_symbol(
                    batch_idx,
                    symbol_values,
                    default_symbol,
                )
                if portfolio_run and not symbol_name:
                    raise ValueError(
                        f"Portfolio Engine.run could not resolve symbol at tick index {batch_idx}."
                    )
                engine._update_symbol_tick(symbol_map, symbol_name, bid, ask)

                entry_signal = 0.0 if entry_values is None else float(entry_values[batch_idx])
                exit_signal = 0.0 if exit_values is None else float(exit_values[batch_idx])
                pending_signal = 0.0 if pending_values is None else float(pending_values[batch_idx])
                cancel_pending_signal = (
                    0.0
                    if cancel_pending_values is None
                    else float(cancel_pending_values[batch_idx])
                )
                pending_signal_2 = (
                    0.0 if pending_values_2 is None else float(pending_values_2[batch_idx])
                )
                cancel_pending_signal_2 = (
                    0.0
                    if cancel_pending_values_2 is None
                    else float(cancel_pending_values_2[batch_idx])
                )
                signal_price = (
                    0.0
                    if signal_price_values is None
                    else float(signal_price_values[batch_idx])
                )
                signal_price_2 = (
                    0.0
                    if signal_price_values_2 is None
                    else float(signal_price_values_2[batch_idx])
                )
                sl_value = 0.0 if sl_values is None else float(sl_values[batch_idx])
                tp_value = 0.0 if tp_values is None else float(tp_values[batch_idx])
                bar_tick_phase = None
                if bar_phase_values is not None:
                    bar_tick_phase = bar_phase_values[batch_idx]
                is_bar_close_flag = _tick_phase_matches(bar_tick_phase, "close")
                is_equity_snapshot_tick = _tick_phase_matches(
                    bar_tick_phase,
                    "open",
                    "high",
                    "low",
                )

                if risk_enabled:
                    if engine._exec_exit_signal(
                        symbol_name,
                        exit_signal,
                        bid,
                        ask,
                        verbose=bool(monitor_verbose),
                    ):
                        engine._schedule_state_dirty = True
                    if engine._exec_cancel_pending_signal(
                        symbol_name,
                        cancel_pending_signal,
                        verbose=bool(monitor_verbose),
                    ):
                        engine._schedule_state_dirty = True
                    if engine._exec_cancel_pending_signal(
                        symbol_name,
                        cancel_pending_signal_2,
                        verbose=bool(monitor_verbose),
                    ):
                        engine._schedule_state_dirty = True

                    if engine._safe_int(entry_signal, 0) in (1, -1):
                        risk_candidates.append(
                            engine._build_risk_candidate(
                                action="entry",
                                symbol_name=symbol_name,
                                signal_code=entry_signal,
                                bid=bid,
                                ask=ask,
                                sl=sl_value,
                                tp=tp_value,
                                requested_volume=run_position_size,
                            )
                        )
                    if engine._safe_int(pending_signal, 0) in (1, -1, 2, -2):
                        risk_candidates.append(
                            engine._build_risk_candidate(
                                action="pending",
                                symbol_name=symbol_name,
                                signal_code=pending_signal,
                                bid=bid,
                                ask=ask,
                                signal_price=signal_price,
                                sl=sl_value,
                                tp=tp_value,
                                requested_volume=run_position_size,
                            )
                        )
                    if engine._safe_int(pending_signal_2, 0) in (1, -1, 2, -2):
                        risk_candidates.append(
                            engine._build_risk_candidate(
                                action="pending",
                                symbol_name=symbol_name,
                                signal_code=pending_signal_2,
                                bid=bid,
                                ask=ask,
                                signal_price=signal_price_2,
                                sl=sl_value,
                                tp=tp_value,
                                requested_volume=run_position_size,
                            )
                        )
                else:
                    if engine._apply_tick_signals(
                        symbol_name=symbol_name,
                        bid=bid,
                        ask=ask,
                        entry_signal=entry_signal,
                        exit_signal=exit_signal,
                        pending_signal=pending_signal,
                        cancel_pending_signal=cancel_pending_signal,
                        pending_signal_2=pending_signal_2,
                        cancel_pending_signal_2=cancel_pending_signal_2,
                        signal_price=signal_price,
                        signal_price_2=signal_price_2,
                        sl=sl_value,
                        tp=tp_value,
                        volume=run_position_size,
                        verbose=bool(monitor_verbose),
                    ):
                        engine._schedule_state_dirty = True

                snapshot_policy = str(
                    getattr(engine, "equity_snapshot_policy", "bar_close") or "bar_close"
                ).lower()
                if snapshot_policy in {"position_update", "every_tick"}:
                    should_snapshot = (
                        is_equity_snapshot_tick if bar_phase_values is not None else True
                    )
                    if should_snapshot and engine._has_open_positions():
                        engine.monitor_positions(verbose=False)
                        engine.monitor_account(verbose=False)
                        engine._schedule_state_dirty = True
                    elif should_snapshot and snapshot_policy == "every_tick":
                        engine.monitor_account(verbose=False)

                engine._run_scheduled_callbacks(
                    tick_number=tick_number,
                    verbose=bool(monitor_verbose),
                    is_bar_close=is_bar_close_flag,
                )
                processed += 1
                if progress_bar is not None:
                    progress_bar.update(1)

            if risk_enabled and engine._execute_risk_batch(
                risk_candidates,
                fallback_volume=run_position_size,
                verbose=bool(monitor_verbose),
            ):
                engine._schedule_state_dirty = True

            if frame_observer is not None:
                frame_observer(
                    engine=engine,
                    timestamp=engine.state.current_tick_datetime,
                    tick_number=processed,
                    batch_end=batch_end,
                )

            idx = batch_end
    finally:
        engine.state.current_tick_datetime = None
        engine.state.current_tick_epoch = None
        if progress_bar is not None:
            progress_bar.close()

    return int(processed)


def _signal_to_float_array(data, col_name_map, names):
    for name in names:
        col = col_name_map.get(name)
        if col is not None:
            return data[col].fillna(0.0).to_numpy(dtype="float64", copy=False)
    return None


def _signal_to_object_array(data, col_name_map, names):
    for name in names:
        col = col_name_map.get(name)
        if col is not None:
            return data[col].to_numpy(copy=False)
    return None


def _tick_phase_matches(value, *phases: str) -> bool:
    if value is None:
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value) if "close" in phases else False
    parts = {
        part.strip().lower()
        for part in str(value).split("|")
        if part is not None and str(part).strip()
    }
    if not parts:
        return False
    return any(str(phase).strip().lower() in parts for phase in phases)

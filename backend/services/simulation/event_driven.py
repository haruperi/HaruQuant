"""Event-driven simulation backend."""

from __future__ import annotations

try:
    from numba import njit
except Exception:  # pragma: no cover - optional dependency fallback
    njit = None

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - optional dependency fallback
    tqdm = None


if njit is not None:
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
    monitor_verbose: bool = False,
    show_progress: bool = False,
    progress_desc: str = "Tester Progress",
    frame_observer=None,
) -> int:
    """Run prepared tick data through the event-driven backend."""
    if data is None:
        return 0
    if position_size is not None and float(position_size) <= 0.0:
        raise ValueError("position_size must be > 0 when provided.")

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

    is_bar_close_values = None
    if "is_bar_close" in col_name_map:
        is_bar_close_values = data[col_name_map["is_bar_close"]].to_numpy(
            dtype="bool",
            copy=False,
        )

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

    schedule_enabled = any(value is not None for value in engine.run_schedule.values())
    risk_enabled = engine._risk_enabled()
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

    engine._schedule_state_dirty = True
    run_position_size = (
        float(engine.default_signal_volume)
        if position_size is None
        else float(position_size)
    )
    processed = 0
    total_ticks = int(bid_values.shape[0])
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
                is_bar_close_flag = False
                if is_bar_close_values is not None:
                    is_bar_close_flag = bool(is_bar_close_values[batch_idx])

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

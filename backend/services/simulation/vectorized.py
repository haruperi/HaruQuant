"""Vectorized simulation backend."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from backend.common.logger import logger
from backend.services.execution import core

try:
    from numba import njit
except Exception:  # pragma: no cover - optional dependency fallback
    njit = None


# Position table columns:
# [ticket, symbol_id, type, open_price, volume, sl, tp, open_tick_idx, status]
POS_TICKET = 0
POS_SYMBOL_ID = 1
POS_TYPE = 2
POS_OPEN_PRICE = 3
POS_VOLUME = 4
POS_SL = 5
POS_TP = 6
POS_OPEN_IDX = 7
POS_STATUS = 8
POS_COLS = 9

# Trade record columns:
# [ticket, symbol_id, type, open_price, close_price, volume, sl, tp,
#  open_idx, close_idx, profit, close_reason, commission]
REC_TICKET = 0
REC_SYMBOL_ID = 1
REC_TYPE = 2
REC_OPEN_PRICE = 3
REC_CLOSE_PRICE = 4
REC_VOLUME = 5
REC_SL = 6
REC_TP = 7
REC_OPEN_IDX = 8
REC_CLOSE_IDX = 9
REC_PROFIT = 10
REC_REASON = 11
REC_COMMISSION = 12
REC_COLS = 13


if njit is not None:
    @njit(cache=True)
    def _run_turbo_sim_numba(
        bid_arr,
        ask_arr,
        symbol_id_arr,
        is_bar_close_arr,
        event_indices,
        entry_signals,
        exit_signals,
        sl_arr,
        tp_arr,
        initial_balance,
        contract_size,
        position_size,
        commission_per_lot,
        slippage_points_arr,
        point_value,
        num_symbols,
        snapshot_requires_open_positions,
        max_positions=100,
    ):
        balance = initial_balance
        active_positions = np.zeros((max_positions, POS_COLS), dtype=np.float64)
        last_bid_by_symbol = np.zeros(num_symbols, dtype=np.float64)
        last_ask_by_symbol = np.zeros(num_symbols, dtype=np.float64)
        completed_trades = np.zeros(
            (len(event_indices) * max_positions, REC_COLS),
            dtype=np.float64,
        )
        completed_count = 0

        bar_close_indices = np.where(is_bar_close_arr)[0]
        equity_curve = np.zeros((len(bar_close_indices), 2), dtype=np.float64)
        equity_ptr = 0
        next_ticket = 1

        for event_ptr in range(len(event_indices)):
            idx = event_indices[event_ptr]
            bid = bid_arr[idx]
            ask = ask_arr[idx]
            symbol_id = symbol_id_arr[idx]
            last_bid_by_symbol[symbol_id] = bid
            last_ask_by_symbol[symbol_id] = ask
            slippage_price = slippage_points_arr[idx] * point_value

            for i in range(max_positions):
                if active_positions[i, POS_STATUS] == 0:
                    continue

                pos_symbol_id = int(active_positions[i, POS_SYMBOL_ID])
                if pos_symbol_id != symbol_id:
                    continue

                p_type = active_positions[i, POS_TYPE]
                p_sl = active_positions[i, POS_SL]
                p_tp = active_positions[i, POS_TP]
                p_vol = active_positions[i, POS_VOLUME]
                p_open = active_positions[i, POS_OPEN_PRICE]

                close_price = -1.0
                reason = 0.0

                if p_type == 0:
                    if p_sl > 0 and bid <= p_sl:
                        close_price = bid - slippage_price
                        reason = 1.0
                    elif p_tp > 0 and bid >= p_tp:
                        close_price = bid - slippage_price
                        reason = 2.0
                else:
                    if p_sl > 0 and ask >= p_sl:
                        close_price = ask + slippage_price
                        reason = 1.0
                    elif p_tp > 0 and ask <= p_tp:
                        close_price = ask + slippage_price
                        reason = 2.0

                if close_price > 0:
                    if p_type == 0:
                        pnl = (close_price - p_open) * p_vol * contract_size
                    else:
                        pnl = (p_open - close_price) * p_vol * contract_size
                    commission = -abs(p_vol * commission_per_lot * 2.0)
                    net_pnl = pnl + commission
                    balance += net_pnl

                    completed_trades[completed_count, REC_TICKET] = active_positions[i, POS_TICKET]
                    completed_trades[completed_count, REC_SYMBOL_ID] = pos_symbol_id
                    completed_trades[completed_count, REC_TYPE] = p_type
                    completed_trades[completed_count, REC_OPEN_PRICE] = p_open
                    completed_trades[completed_count, REC_CLOSE_PRICE] = close_price
                    completed_trades[completed_count, REC_VOLUME] = p_vol
                    completed_trades[completed_count, REC_SL] = p_sl
                    completed_trades[completed_count, REC_TP] = p_tp
                    completed_trades[completed_count, REC_OPEN_IDX] = active_positions[i, POS_OPEN_IDX]
                    completed_trades[completed_count, REC_CLOSE_IDX] = idx
                    completed_trades[completed_count, REC_PROFIT] = pnl
                    completed_trades[completed_count, REC_REASON] = reason
                    completed_trades[completed_count, REC_COMMISSION] = commission
                    completed_count += 1
                    active_positions[i, POS_STATUS] = 0

            exit_sig = exit_signals[idx]
            if exit_sig != 0:
                target_type = 0 if exit_sig == 1 else 1
                for i in range(max_positions):
                    if (
                        active_positions[i, POS_STATUS] == 1
                        and active_positions[i, POS_SYMBOL_ID] == symbol_id
                        and active_positions[i, POS_TYPE] == target_type
                    ):
                        p_vol = active_positions[i, POS_VOLUME]
                        p_open = active_positions[i, POS_OPEN_PRICE]
                        close_price = (
                            bid - slippage_price
                            if target_type == 0
                            else ask + slippage_price
                        )
                        if target_type == 0:
                            pnl = (close_price - p_open) * p_vol * contract_size
                        else:
                            pnl = (p_open - close_price) * p_vol * contract_size
                        commission = -abs(p_vol * commission_per_lot * 2.0)
                        net_pnl = pnl + commission
                        balance += net_pnl

                        completed_trades[completed_count, REC_TICKET] = active_positions[i, POS_TICKET]
                        completed_trades[completed_count, REC_SYMBOL_ID] = symbol_id
                        completed_trades[completed_count, REC_TYPE] = target_type
                        completed_trades[completed_count, REC_OPEN_PRICE] = p_open
                        completed_trades[completed_count, REC_CLOSE_PRICE] = close_price
                        completed_trades[completed_count, REC_VOLUME] = p_vol
                        completed_trades[completed_count, REC_SL] = active_positions[i, POS_SL]
                        completed_trades[completed_count, REC_TP] = active_positions[i, POS_TP]
                        completed_trades[completed_count, REC_OPEN_IDX] = active_positions[i, POS_OPEN_IDX]
                        completed_trades[completed_count, REC_CLOSE_IDX] = idx
                        completed_trades[completed_count, REC_PROFIT] = pnl
                        completed_trades[completed_count, REC_REASON] = 3.0
                        completed_trades[completed_count, REC_COMMISSION] = commission
                        completed_count += 1
                        active_positions[i, POS_STATUS] = 0

            entry_sig = entry_signals[idx]
            if entry_sig != 0:
                slot = -1
                for i in range(max_positions):
                    if active_positions[i, POS_STATUS] == 0:
                        slot = i
                        break

                if slot != -1:
                    e_type = 0 if entry_sig == 1 else 1
                    e_price = (
                        ask + slippage_price
                        if e_type == 0
                        else bid - slippage_price
                    )
                    active_positions[slot, POS_TICKET] = next_ticket
                    active_positions[slot, POS_SYMBOL_ID] = symbol_id
                    active_positions[slot, POS_TYPE] = e_type
                    active_positions[slot, POS_OPEN_PRICE] = e_price
                    active_positions[slot, POS_VOLUME] = position_size
                    active_positions[slot, POS_SL] = sl_arr[idx]
                    active_positions[slot, POS_TP] = tp_arr[idx]
                    active_positions[slot, POS_OPEN_IDX] = idx
                    active_positions[slot, POS_STATUS] = 1
                    next_ticket += 1

            if is_bar_close_arr[idx]:
                has_open_positions = False
                unrealized = 0.0
                for i in range(max_positions):
                    if active_positions[i, POS_STATUS] == 1:
                        has_open_positions = True
                        pos_symbol_id = int(active_positions[i, POS_SYMBOL_ID])
                        p_type = active_positions[i, POS_TYPE]
                        p_open = active_positions[i, POS_OPEN_PRICE]
                        p_vol = active_positions[i, POS_VOLUME]
                        p_bid = last_bid_by_symbol[pos_symbol_id]
                        p_ask = last_ask_by_symbol[pos_symbol_id]
                        if p_bid <= 0.0 or p_ask <= 0.0:
                            continue
                        p_price = p_bid if p_type == 0 else p_ask
                        if p_type == 0:
                            unrealized += (p_price - p_open) * p_vol * contract_size
                        else:
                            unrealized += (p_open - p_price) * p_vol * contract_size

                if snapshot_requires_open_positions and not has_open_positions:
                    continue

                equity_curve[equity_ptr, 0] = idx
                equity_curve[equity_ptr, 1] = balance + unrealized
                equity_ptr += 1

        return completed_trades[:completed_count], equity_curve[:equity_ptr], balance


def run_vectorized_simulation(
    engine,
    data,
    initial_balance: float = 10000.0,
    contract_size: float = 100000.0,
    position_size: float = 0.01,
    commission_per_lot: float = 0.0,
    slippage_model: str = "none",
    slippage_points: float = 0.0,
    slippage_min: float | None = None,
    slippage_max: float | None = None,
    point_value: float = 0.00001,
) -> int:
    """Run the vectorized simulation backend and update engine state."""
    if float(position_size) <= 0.0:
        raise ValueError("position_size must be > 0.")
    resolved_slippage_points = _resolve_slippage_points_array(
        slippage_model,
        slippage_points,
        slippage_min,
        slippage_max,
        len(data),
    )
    if njit is None:
        logger.warning("Numba not available. Falling back to run_event_driven().")
        return int(
            engine.run_event_driven(
                data,
                position_size=position_size,
                commission_per_lot=commission_per_lot,
                slippage_model=slippage_model,
                slippage_points=slippage_points,
                slippage_min=slippage_min,
                slippage_max=slippage_max,
            )
            or 0
        )

    start_time = time.time()
    snapshot_policy = str(
        getattr(engine, "equity_snapshot_policy", "bar_close") or "bar_close"
    ).lower()
    prepared = prepare_vectorized_data(data, snapshot_policy=snapshot_policy)
    trades_arr, equity_arr, final_balance = _run_turbo_sim_numba(
        prepared["bid_arr"],
        prepared["ask_arr"],
        prepared["symbol_id_arr"],
        prepared["is_bar_close_arr"],
        prepared["event_indices"],
        prepared["entry_signals"],
        prepared["exit_signals"],
        prepared["sl_arr"],
        prepared["tp_arr"],
        float(initial_balance),
        float(contract_size),
        float(position_size),
        float(commission_per_lot),
        resolved_slippage_points,
        float(point_value),
        int(len(prepared["id_to_symbol"])),
        bool(snapshot_policy == "position_update"),
    )

    engine.state.completed_trade_records = reconstruct_trades(
        trades_arr,
        prepared,
        float(contract_size),
        engine=engine,
    )

    trade_deltas = []
    total_delta = 0.0
    for i in range(len(trades_arr)):
        original_profit = trades_arr[i, REC_PROFIT]
        corrected_profit = engine.state.completed_trade_records[i].profit_loss
        delta = corrected_profit - original_profit
        total_delta += delta
        trade_deltas.append((int(trades_arr[i, REC_CLOSE_IDX]), delta))

    trade_deltas.sort(key=lambda x: x[0])

    engine.state.completed_equity_curve = reconstruct_equity_curve(
        equity_arr,
        prepared,
        trade_deltas=trade_deltas,
    )
    corrected_final_balance = final_balance + total_delta
    engine.state.trading_account.balance = corrected_final_balance
    engine.state.trading_account.equity = corrected_final_balance

    logger.info(f"Turbo run completed in {time.time() - start_time:.4f}s")
    return int(len(data))


def prepare_vectorized_data(data, snapshot_policy: str = "position_update") -> dict:
    """Prepare contiguous numpy arrays for the vectorized backend."""
    col_name_map = {str(col).lower(): col for col in data.columns}

    bid_arr = data[col_name_map["bid"]].to_numpy(dtype="float64", copy=False)
    ask_arr = data[col_name_map["ask"]].to_numpy(dtype="float64", copy=False)
    bar_phase_arr = data[col_name_map["is_bar_close"]].to_numpy(copy=False)
    snapshot_policy_normalized = str(snapshot_policy or "bar_close").strip().lower()
    phases = ("close",) if snapshot_policy_normalized == "bar_close" else ("open", "high", "low")
    is_bar_close_arr = _bar_phase_mask(
        bar_phase_arr,
        phases=phases,
    )

    symbol_series = data[col_name_map["symbol"]].astype(str)
    unique_symbols = symbol_series.unique()
    symbol_to_id = {name: i for i, name in enumerate(unique_symbols)}
    id_to_symbol = {i: name for name, i in symbol_to_id.items()}
    symbol_id_arr = symbol_series.map(symbol_to_id).to_numpy(dtype="int64")

    entry_signals = _signal_to_float_array(data, col_name_map, ["entry_signal"])
    if entry_signals is None:
        entry_signals = np.zeros(len(data))
    exit_signals = _signal_to_float_array(data, col_name_map, ["exit_signal"])
    if exit_signals is None:
        exit_signals = np.zeros(len(data))
    sl_arr = _signal_to_float_array(data, col_name_map, ["sl", "stop_loss"])
    if sl_arr is None:
        sl_arr = np.zeros(len(data))
    tp_arr = _signal_to_float_array(data, col_name_map, ["tp", "take_profit"])
    if tp_arr is None:
        tp_arr = np.zeros(len(data))

    event_mask = (entry_signals != 0) | (exit_signals != 0) | is_bar_close_arr
    event_indices = np.where(event_mask)[0]

    return {
        "bid_arr": bid_arr,
        "ask_arr": ask_arr,
        "symbol_id_arr": symbol_id_arr,
        "is_bar_close_arr": is_bar_close_arr,
        "event_indices": event_indices,
        "entry_signals": entry_signals,
        "exit_signals": exit_signals,
        "sl_arr": sl_arr,
        "tp_arr": tp_arr,
        "id_to_symbol": id_to_symbol,
        "timestamps": (
            data.index.to_pydatetime() if isinstance(data.index, pd.DatetimeIndex) else None
        ),
    }


def reconstruct_trades(trades_arr, prepared: dict, contract_size: float, engine=None) -> list:
    id_to_symbol = prepared["id_to_symbol"]
    timestamps = prepared["timestamps"]
    bid_arr = prepared["bid_arr"]
    ask_arr = prepared["ask_arr"]
    reconstructed = []

    for i in range(len(trades_arr)):
        row = trades_arr[i]
        symbol_name = id_to_symbol[int(row[REC_SYMBOL_ID])]
        open_idx = int(row[REC_OPEN_IDX])
        close_idx = int(row[REC_CLOSE_IDX])
        is_buy = row[REC_TYPE] == 0
        price_slice = bid_arr[open_idx : close_idx + 1] if is_buy else ask_arr[open_idx : close_idx + 1]

        profit_loss = row[REC_PROFIT]
        if engine is not None and hasattr(engine, "_strict_order_calc_profit"):
            try:
                # MT5 types: BUY=0, SELL=1. Vectorized matches this: REC_TYPE 0=BUY, 1=SELL
                profit_loss = engine._strict_order_calc_profit(
                    int(row[REC_TYPE]),
                    symbol_name,
                    row[REC_VOLUME],
                    row[REC_OPEN_PRICE],
                    row[REC_CLOSE_PRICE],
                )
            except Exception as e:
                logger.warning(
                    f"Vectorized post-processing: order_calc_profit failed for {symbol_name}: {e}"
                )

        mfe_usd = 0.0
        mae_usd = 0.0
        if len(price_slice) > 0:
            p_open = row[REC_OPEN_PRICE]
            p_vol = row[REC_VOLUME]
            if is_buy:
                mfe_usd = (np.max(price_slice) - p_open) * p_vol * contract_size
                mae_usd = (np.min(price_slice) - p_open) * p_vol * contract_size
            else:
                mfe_usd = (p_open - np.min(price_slice)) * p_vol * contract_size
                mae_usd = (p_open - np.max(price_slice)) * p_vol * contract_size

        reason_map = {1.0: "stop_loss", 2.0: "take_profit", 3.0: "signal"}
        reason = reason_map.get(row[REC_REASON], "manual")
        reconstructed.append(
            core.TradeRecord(
                ticket=int(row[REC_TICKET]),
                symbol=symbol_name,
                type="buy" if is_buy else "sell",
                open_price=row[REC_OPEN_PRICE],
                close_price=row[REC_CLOSE_PRICE],
                size=row[REC_VOLUME],
                stop_loss_price=row[REC_SL],
                profit_target_price=row[REC_TP],
                open_time=timestamps[open_idx] if timestamps is not None else None,
                close_time=timestamps[close_idx] if timestamps is not None else None,
                profit_loss=profit_loss,
                commission=row[REC_COMMISSION] if len(row) > REC_COMMISSION else 0.0,
                mfe_usd=mfe_usd,
                mae_usd=mae_usd,
                exit_reason=reason,
                close_type=reason.upper(),
            )
        )

    return reconstructed


def _resolve_slippage_points_array(
    slippage_model: str,
    slippage_points: float,
    slippage_min: float | None,
    slippage_max: float | None,
    length: int,
):
    model = str(slippage_model or "none").strip().lower()
    if model in {"", "none", "disabled"}:
        return np.zeros(int(length), dtype=np.float64)
    if model == "fixed":
        return np.full(
            int(length),
            max(0.0, float(slippage_points or 0.0)),
            dtype=np.float64,
        )
    low = max(0.0, float(slippage_min or 0.0))
    high = max(low, float(slippage_max if slippage_max is not None else low))
    if high <= low:
        return np.full(int(length), low, dtype=np.float64)
    rng = np.random.default_rng(42)
    return rng.uniform(low, high, int(length)).astype(np.float64)


def reconstruct_equity_curve(equity_arr, prepared: dict, trade_deltas=None) -> list:
    timestamps = prepared["timestamps"]
    reconstructed = []
    
    cumulative_delta = 0.0
    delta_ptr = 0
    num_deltas = len(trade_deltas) if trade_deltas else 0
    
    for i in range(len(equity_arr)):
        tick_idx = int(equity_arr[i, 0])
        value = equity_arr[i, 1]
        
        if trade_deltas:
            while delta_ptr < num_deltas and trade_deltas[delta_ptr][0] <= tick_idx:
                cumulative_delta += trade_deltas[delta_ptr][1]
                delta_ptr += 1
        
        corrected_value = value + cumulative_delta
        reconstructed.append(
            core.EquityPoint(
                timestamp=timestamps[tick_idx] if timestamps is not None else None,
                balance=corrected_value,
                equity=corrected_value,
            )
        )
    return reconstructed


def _signal_to_float_array(data, col_name_map: dict[str, object], names: list[str]):
    for name in names:
        col = col_name_map.get(name)
        if col is not None:
            return data[col].fillna(0.0).to_numpy(dtype="float64", copy=False)
    return None


def _bar_phase_mask(values, phases: tuple[str, ...]) -> np.ndarray:
    target = {str(phase).strip().lower() for phase in phases}
    mask = np.zeros(len(values), dtype=bool)
    for idx, value in enumerate(values):
        if isinstance(value, (bool, np.bool_)):
            mask[idx] = bool(value) if "close" in target else False
            continue
        parts = {
            part.strip().lower()
            for part in str(value).split("|")
            if part is not None and str(part).strip()
        }
        mask[idx] = bool(parts & target)
    return mask

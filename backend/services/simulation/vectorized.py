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
#  open_idx, close_idx, profit, close_reason]
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
REC_COLS = 12


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
        max_positions=100,
    ):
        balance = initial_balance
        active_positions = np.zeros((max_positions, POS_COLS), dtype=np.float64)
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
                        close_price = bid
                        reason = 1.0
                    elif p_tp > 0 and bid >= p_tp:
                        close_price = bid
                        reason = 2.0
                else:
                    if p_sl > 0 and ask >= p_sl:
                        close_price = ask
                        reason = 1.0
                    elif p_tp > 0 and ask <= p_tp:
                        close_price = ask
                        reason = 2.0

                if close_price > 0:
                    if p_type == 0:
                        pnl = (close_price - p_open) * p_vol * contract_size
                    else:
                        pnl = (p_open - close_price) * p_vol * contract_size
                    balance += pnl

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
                        close_price = bid if target_type == 0 else ask
                        if target_type == 0:
                            pnl = (close_price - p_open) * p_vol * contract_size
                        else:
                            pnl = (p_open - close_price) * p_vol * contract_size
                        balance += pnl

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
                    e_price = ask if e_type == 0 else bid
                    active_positions[slot, POS_TICKET] = next_ticket
                    active_positions[slot, POS_SYMBOL_ID] = symbol_id
                    active_positions[slot, POS_TYPE] = e_type
                    active_positions[slot, POS_OPEN_PRICE] = e_price
                    active_positions[slot, POS_VOLUME] = 0.01
                    active_positions[slot, POS_SL] = sl_arr[idx]
                    active_positions[slot, POS_TP] = tp_arr[idx]
                    active_positions[slot, POS_OPEN_IDX] = idx
                    active_positions[slot, POS_STATUS] = 1
                    next_ticket += 1

            if is_bar_close_arr[idx]:
                unrealized = 0.0
                for i in range(max_positions):
                    if active_positions[i, POS_STATUS] == 1:
                        if active_positions[i, POS_SYMBOL_ID] == symbol_id:
                            p_type = active_positions[i, POS_TYPE]
                            p_open = active_positions[i, POS_OPEN_PRICE]
                            p_vol = active_positions[i, POS_VOLUME]
                            p_price = bid if p_type == 0 else ask
                            if p_type == 0:
                                unrealized += (p_price - p_open) * p_vol * contract_size
                            else:
                                unrealized += (p_open - p_price) * p_vol * contract_size

                equity_curve[equity_ptr, 0] = idx
                equity_curve[equity_ptr, 1] = balance + unrealized
                equity_ptr += 1

        return completed_trades[:completed_count], equity_curve[:equity_ptr], balance


def run_vectorized_simulation(
    engine,
    data,
    initial_balance: float = 10000.0,
    contract_size: float = 100000.0,
) -> int:
    """Run the vectorized simulation backend and update engine state."""
    if njit is None:
        logger.warning("Numba not available. Falling back to run_event_driven().")
        return int(engine.run_event_driven(data) or 0)

    start_time = time.time()
    prepared = prepare_vectorized_data(data)
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
    )

    engine.state.completed_trade_records = reconstruct_trades(
        trades_arr,
        prepared,
        float(contract_size),
    )
    engine.state.completed_equity_curve = reconstruct_equity_curve(
        equity_arr,
        prepared,
    )
    engine.state.trading_account.balance = final_balance
    engine.state.trading_account.equity = final_balance

    logger.info(f"Turbo run completed in {time.time() - start_time:.4f}s")
    return int(len(data))


def prepare_vectorized_data(data) -> dict:
    """Prepare contiguous numpy arrays for the vectorized backend."""
    col_name_map = {str(col).lower(): col for col in data.columns}

    bid_arr = data[col_name_map["bid"]].to_numpy(dtype="float64", copy=False)
    ask_arr = data[col_name_map["ask"]].to_numpy(dtype="float64", copy=False)
    is_bar_close_arr = data[col_name_map["is_bar_close"]].to_numpy(
        dtype="bool",
        copy=False,
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


def reconstruct_trades(trades_arr, prepared: dict, contract_size: float) -> list:
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
                profit_loss=row[REC_PROFIT],
                mfe_usd=mfe_usd,
                mae_usd=mae_usd,
                exit_reason=reason,
                close_type=reason.upper(),
            )
        )

    return reconstructed


def reconstruct_equity_curve(equity_arr, prepared: dict) -> list:
    timestamps = prepared["timestamps"]
    reconstructed = []
    for i in range(len(equity_arr)):
        tick_idx = int(equity_arr[i, 0])
        value = equity_arr[i, 1]
        reconstructed.append(
            core.EquityPoint(
                timestamp=timestamps[tick_idx] if timestamps is not None else None,
                balance=value,
                equity=value,
            )
        )
    return reconstructed


def _signal_to_float_array(data, col_name_map: dict[str, object], names: list[str]):
    for name in names:
        col = col_name_map.get(name)
        if col is not None:
            return data[col].fillna(0.0).to_numpy(dtype="float64", copy=False)
    return None

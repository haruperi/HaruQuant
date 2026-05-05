"""
Vectorized simulation backend_retiring.

Optimized for state-of-the-art performance using a Kernel-Resident Architecture.
All core simulation logic runs inside JIT-compiled Numba kernels with zero-object
hot loops and pre-allocated NumPy memory layouts.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from services.utils.logger import logger
from services.execution import core

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
        max_positions=200,
    ):
        balance = initial_balance
        active_positions = np.empty((max_positions, POS_COLS), dtype=np.float64)
        for i in range(max_positions):
            active_positions[i, POS_STATUS] = 0.0
            
        # Active slot tracker to avoid O(N*M) scans
        active_slots = np.zeros(max_positions, dtype=np.int32)
        num_active_slots = 0

        last_bid_by_symbol = np.zeros(num_symbols, dtype=np.float64)
        last_ask_by_symbol = np.zeros(num_symbols, dtype=np.float64)
        
        completed_trades = np.empty(
            (min(1000000, len(event_indices) * 2), REC_COLS),
            dtype=np.float64,
        )
        completed_count = 0
        max_completed = len(completed_trades)

        bar_close_indices = np.where(is_bar_close_arr)[0]
        equity_curve = np.empty((len(bar_close_indices), 2), dtype=np.float64)
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

            # 1. Process Active Positions (SL/TP)
            s_ptr = 0
            while s_ptr < num_active_slots:
                slot = active_slots[s_ptr]
                pos_symbol_id = int(active_positions[slot, POS_SYMBOL_ID])
                
                # Only check SL/TP for the current symbol's positions
                if pos_symbol_id == symbol_id:
                    p_type = active_positions[slot, POS_TYPE]
                    p_sl = active_positions[slot, POS_SL]
                    p_tp = active_positions[slot, POS_TP]
                    p_vol = active_positions[slot, POS_VOLUME]
                    p_open = active_positions[slot, POS_OPEN_PRICE]

                    close_price = -1.0
                    reason = 0.0

                    if p_type == 0: # BUY
                        if p_sl > 0.0 and bid <= p_sl:
                            close_price = bid - slippage_price; reason = 1.0
                        elif p_tp > 0.0 and bid >= p_tp:
                            close_price = bid - slippage_price; reason = 2.0
                    else: # SELL
                        if p_sl > 0.0 and ask >= p_sl:
                            close_price = ask + slippage_price; reason = 1.0
                        elif p_tp > 0.0 and ask <= p_tp:
                            close_price = ask + slippage_price; reason = 2.0

                    if close_price > 0.0:
                        pnl = (close_price - p_open) * p_vol * contract_size if p_type == 0 else (p_open - close_price) * p_vol * contract_size
                        commission = -abs(p_vol * commission_per_lot * 2.0)
                        balance += pnl + commission

                        if completed_count < max_completed:
                            completed_trades[completed_count, REC_TICKET] = active_positions[slot, POS_TICKET]
                            completed_trades[completed_count, REC_SYMBOL_ID] = pos_symbol_id
                            completed_trades[completed_count, REC_TYPE] = p_type
                            completed_trades[completed_count, REC_OPEN_PRICE] = p_open
                            completed_trades[completed_count, REC_CLOSE_PRICE] = close_price
                            completed_trades[completed_count, REC_VOLUME] = p_vol
                            completed_trades[completed_count, REC_SL] = p_sl
                            completed_trades[completed_count, REC_TP] = p_tp
                            completed_trades[completed_count, REC_OPEN_IDX] = active_positions[slot, POS_OPEN_IDX]
                            completed_trades[completed_count, REC_CLOSE_IDX] = idx
                            completed_trades[completed_count, REC_PROFIT] = pnl
                            completed_trades[completed_count, REC_REASON] = reason
                            completed_trades[completed_count, REC_COMMISSION] = commission
                            completed_count += 1
                        
                        active_positions[slot, POS_STATUS] = 0.0
                        # Remove from active slots
                        active_slots[s_ptr] = active_slots[num_active_slots - 1]
                        num_active_slots -= 1
                        continue # Don't increment s_ptr, we swapped a new slot into this position
                s_ptr += 1

            # 2. Exit Signal Check
            exit_sig = exit_signals[idx]
            if exit_sig != 0.0:
                target_type = 0 if exit_sig == 1 else 1
                s_ptr = 0
                while s_ptr < num_active_slots:
                    slot = active_slots[s_ptr]
                    if (
                        active_positions[slot, POS_SYMBOL_ID] == symbol_id
                        and active_positions[slot, POS_TYPE] == target_type
                    ):
                        p_vol = active_positions[slot, POS_VOLUME]
                        p_open = active_positions[slot, POS_OPEN_PRICE]
                        close_price = bid - slippage_price if target_type == 0 else ask + slippage_price
                        pnl = (close_price - p_open) * p_vol * contract_size if target_type == 0 else (p_open - close_price) * p_vol * contract_size
                        commission = -abs(p_vol * commission_per_lot * 2.0)
                        balance += pnl + commission

                        if completed_count < max_completed:
                            completed_trades[completed_count, REC_TICKET] = active_positions[slot, POS_TICKET]
                            completed_trades[completed_count, REC_SYMBOL_ID] = symbol_id
                            completed_trades[completed_count, REC_TYPE] = target_type
                            completed_trades[completed_count, REC_OPEN_PRICE] = p_open
                            completed_trades[completed_count, REC_CLOSE_PRICE] = close_price
                            completed_trades[completed_count, REC_VOLUME] = p_vol
                            completed_trades[completed_count, REC_SL] = active_positions[slot, POS_SL]
                            completed_trades[completed_count, REC_TP] = active_positions[slot, POS_TP]
                            completed_trades[completed_count, REC_OPEN_IDX] = active_positions[slot, POS_OPEN_IDX]
                            completed_trades[completed_count, REC_CLOSE_IDX] = idx
                            completed_trades[completed_count, REC_PROFIT] = pnl
                            completed_trades[completed_count, REC_REASON] = 3.0
                            completed_trades[completed_count, REC_COMMISSION] = commission
                            completed_count += 1
                        
                        active_positions[slot, POS_STATUS] = 0.0
                        active_slots[s_ptr] = active_slots[num_active_slots - 1]
                        num_active_slots -= 1
                        continue
                    s_ptr += 1

            # 3. Entry Signal Check
            entry_sig = entry_signals[idx]
            if entry_sig != 0.0 and num_active_slots < max_positions:
                # Find first empty slot in active_positions
                slot = -1
                for i in range(max_positions):
                    if active_positions[i, POS_STATUS] == 0.0:
                        slot = i
                        break
                
                if slot != -1:
                    e_type = 0 if entry_sig == 1 else 1
                    active_positions[slot, POS_TICKET] = next_ticket
                    active_positions[slot, POS_SYMBOL_ID] = symbol_id
                    active_positions[slot, POS_TYPE] = e_type
                    active_positions[slot, POS_OPEN_PRICE] = ask + slippage_price if e_type == 0 else bid - slippage_price
                    active_positions[slot, POS_VOLUME] = position_size
                    active_positions[slot, POS_SL] = sl_arr[idx]
                    active_positions[slot, POS_TP] = tp_arr[idx]
                    active_positions[slot, POS_OPEN_IDX] = idx
                    active_positions[slot, POS_STATUS] = 1.0
                    
                    active_slots[num_active_slots] = slot
                    num_active_slots += 1
                    next_ticket += 1

            # 4. Equity Snapshot
            if is_bar_close_arr[idx]:
                unrealized = 0.0
                if not (snapshot_requires_open_positions and num_active_slots == 0):
                    for s_ptr in range(num_active_slots):
                        slot = active_slots[s_ptr]
                        p_sid = int(active_positions[slot, POS_SYMBOL_ID])
                        p_price = last_bid_by_symbol[p_sid] if active_positions[slot, POS_TYPE] == 0 else last_ask_by_symbol[p_sid]
                        if p_price > 0.0:
                            unrealized += (p_price - active_positions[slot, POS_OPEN_PRICE]) * active_positions[slot, POS_VOLUME] * contract_size if active_positions[slot, POS_TYPE] == 0 else (active_positions[slot, POS_OPEN_PRICE] - p_price) * active_positions[slot, POS_VOLUME] * contract_size
                    
                    equity_curve[equity_ptr, 0] = idx
                    equity_curve[equity_ptr, 1] = balance + unrealized
                    equity_ptr += 1

        # Final pass to collect open positions for post-processing
        open_positions = np.empty((num_active_slots, POS_COLS), dtype=np.float64)
        for s_ptr in range(num_active_slots):
            slot = active_slots[s_ptr]
            open_positions[s_ptr] = active_positions[slot]

        return (
            completed_trades[:completed_count],
            equity_curve[:equity_ptr],
            balance,
            open_positions,
            last_bid_by_symbol,
            last_ask_by_symbol,
        )


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
    kernel_result = _run_turbo_sim_numba(
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
    if len(kernel_result) == 3:
        trades_arr, equity_arr, final_balance = kernel_result
        open_pos_arr = np.empty((0, POS_COLS))
        last_bids = np.zeros(int(len(prepared["id_to_symbol"])))
        last_asks = np.zeros(int(len(prepared["id_to_symbol"])))
    else:
        (
            trades_arr,
            equity_arr,
            final_balance,
            open_pos_arr,
            last_bids,
            last_asks,
        ) = kernel_result

    # MT5 PnL Post-Processing logic
    # We want to converge the simple (close-open)*vol calculations to MT5's precise formulas
    # which handle non-USD accounts, currency conversions, and specific symbol contract types.
    client_available = getattr(engine, "client", None) is not None or hasattr(
        engine,
        "_strict_order_calc_profit",
    )
    fast_mode = bool(getattr(engine, "fast_mode", False))
    
    # We use MT5 if available and NOT in super-fast mode, OR if explicitly requested.
    use_mt5_pnl = client_available and (not fast_mode or getattr(engine, "force_mt5_pnl", False))

    engine.state.completed_trade_records = reconstruct_trades(
        trades_arr,
        prepared,
        float(contract_size),
        engine=engine,
        use_mt5=use_mt5_pnl,
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

    # Calculate unrealized delta for open positions at the end of simulation
    total_unrealized_delta = 0.0
    if use_mt5_pnl and len(open_pos_arr) > 0:
        id_to_symbol = prepared["id_to_symbol"]
        
        for i in range(len(open_pos_arr)):
            pos = open_pos_arr[i]
            sid = int(pos[POS_SYMBOL_ID])
            p_type = int(pos[POS_TYPE])
            p_vol = pos[POS_VOLUME]
            p_open = pos[POS_OPEN_PRICE]
            
            # Use the last known bid/ask for the specific symbol from the kernel
            close_price = last_bids[sid] if p_type == 0 else last_asks[sid]
            
            # Simple unrealized used in kernel
            simple_unrealized = (
                (close_price - p_open) * p_vol * contract_size 
                if p_type == 0 else 
                (p_open - close_price) * p_vol * contract_size
            )
            
            try:
                mt5_unrealized = engine._strict_order_calc_profit(
                    p_type,
                    id_to_symbol[sid],
                    p_vol,
                    p_open,
                    close_price
                )
                total_unrealized_delta += (mt5_unrealized - simple_unrealized)
            except Exception:
                pass

    engine.state.completed_equity_curve = reconstruct_equity_curve(
        equity_arr,
        prepared,
        trade_deltas=trade_deltas,
    )
    
    # Apply unrealized delta to the last equity point if applicable
    if engine.state.completed_equity_curve and total_unrealized_delta != 0:
        last_point = engine.state.completed_equity_curve[-1]
        last_point.balance += 0.0 # Balance doesn't include unrealized
        last_point.equity += total_unrealized_delta

    corrected_final_balance = final_balance + total_delta
    engine.state.trading_account.balance = corrected_final_balance
    if engine.state.completed_equity_curve:
        # Final equity is the corrected last point of the curve
        engine.state.trading_account.equity = engine.state.completed_equity_curve[-1].equity
    else:
        engine.state.trading_account.equity = corrected_final_balance

    logger.info(f"Turbo run completed in {time.time() - start_time:.4f}s")
    return int(len(data))


def prepare_vectorized_data(data, snapshot_policy: str = "position_update") -> dict:
    """Prepare contiguous numpy arrays for the vectorized backend_retiring."""
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


@njit(cache=True)
def _reconstruct_mfe_mae_kernel(trades_arr, bid_arr, ask_arr, contract_size):
    n_trades = len(trades_arr)
    mfe_vals = np.zeros(n_trades)
    mae_vals = np.zeros(n_trades)
    
    for i in range(n_trades):
        open_idx = int(trades_arr[i, REC_OPEN_IDX])
        close_idx = int(trades_arr[i, REC_CLOSE_IDX])
        is_buy = trades_arr[i, REC_TYPE] == 0
        p_open = trades_arr[i, REC_OPEN_PRICE]
        p_vol = trades_arr[i, REC_VOLUME]
        
        # Slice calculation in Numba is very fast
        if is_buy:
            price_slice = bid_arr[open_idx : close_idx + 1]
            if len(price_slice) > 0:
                mx = price_slice[0]
                mn = price_slice[0]
                for p in price_slice:
                    if p > mx: mx = p
                    if p < mn: mn = p
                mfe_vals[i] = (mx - p_open) * p_vol * contract_size
                mae_vals[i] = (mn - p_open) * p_vol * contract_size
        else:
            price_slice = ask_arr[open_idx : close_idx + 1]
            if len(price_slice) > 0:
                mx = price_slice[0]
                mn = price_slice[0]
                for p in price_slice:
                    if p > mx: mx = p
                    if p < mn: mn = p
                mfe_vals[i] = (p_open - mn) * p_vol * contract_size
                mae_vals[i] = (p_open - mx) * p_vol * contract_size
    return mfe_vals, mae_vals


def reconstruct_trades(trades_arr, prepared: dict, contract_size: float, engine=None, use_mt5: bool = False) -> list:
    id_to_symbol = prepared["id_to_symbol"]
    timestamps = prepared["timestamps"]
    
    # Fast path for MFE/MAE
    mfe_vals, mae_vals = _reconstruct_mfe_mae_kernel(
        trades_arr, 
        prepared["bid_arr"], 
        prepared["ask_arr"], 
        float(contract_size)
    )
    
    reconstructed = []
    reason_map = {1.0: "stop_loss", 2.0: "take_profit", 3.0: "signal"}

    # If use_mt5 is True, ensure we have the function
    use_mt5 = use_mt5 and engine is not None and hasattr(engine, "_strict_order_calc_profit")

    for i in range(len(trades_arr)):
        row = trades_arr[i]
        symbol_name = id_to_symbol[int(row[REC_SYMBOL_ID])]
        
        profit_loss = row[REC_PROFIT]
        if use_mt5:
            try:
                profit_loss = engine._strict_order_calc_profit(
                    int(row[REC_TYPE]),
                    symbol_name,
                    row[REC_VOLUME],
                    row[REC_OPEN_PRICE],
                    row[REC_CLOSE_PRICE],
                )
            except Exception:
                pass

        reason = reason_map.get(row[REC_REASON], "manual")
        reconstructed.append(
            core.TradeRecord(
                ticket=int(row[REC_TICKET]),
                symbol=symbol_name,
                type="buy" if row[REC_TYPE] == 0 else "sell",
                open_price=row[REC_OPEN_PRICE],
                close_price=row[REC_CLOSE_PRICE],
                size=row[REC_VOLUME],
                stop_loss_price=row[REC_SL],
                profit_target_price=row[REC_TP],
                open_time=timestamps[int(row[REC_OPEN_IDX])] if timestamps is not None else None,
                close_time=timestamps[int(row[REC_CLOSE_IDX])] if timestamps is not None else None,
                profit_loss=profit_loss,
                commission=row[REC_COMMISSION] if len(row) > REC_COMMISSION else 0.0,
                mfe_usd=mfe_vals[i],
                mae_usd=mae_vals[i],
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

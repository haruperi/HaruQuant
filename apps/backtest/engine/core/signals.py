"""
Signal Preparation Module.

Converts strategy signals from various formats to NumPy arrays
optimized for the fast simulation core.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def prepare_signals_from_dataframe(
    data: pd.DataFrame,
    entry_column: str = "entry_signal",
    exit_column: str = "exit_signal",
    sl_column: Optional[str] = "sl",
    tp_column: Optional[str] = "tp",
    size_column: Optional[str] = "size",
    default_size: float = 0.1,
) -> Dict[str, np.ndarray]:
    """
    Convert DataFrame signals to NumPy arrays for fast simulation.

    Handles the standard HaruQuant signal format where:
    - entry_signal: 1 = buy, -1 = sell, 0 = none
    - exit_signal: 1 = exit long, -1 = exit short, 0 = none

    Args:
        data: DataFrame with OHLCV and signal columns
        entry_column: Column name for entry signals
        exit_column: Column name for exit signals
        sl_column: Column name for stop loss prices (optional)
        tp_column: Column name for take profit prices (optional)
        size_column: Column name for position sizes (optional)
        default_size: Default position size if size_column not provided

    Returns:
        dict with NumPy arrays:
            - entry_signals: int8
            - exit_signals: int8
            - stop_losses: float64
            - take_profits: float64
            - sizes: float64
    """
    n = len(data)

    result = {
        "entry_signals": np.zeros(n, dtype=np.int8),
        "exit_signals": np.zeros(n, dtype=np.int8),
        "stop_losses": np.zeros(n, dtype=np.float64),
        "take_profits": np.zeros(n, dtype=np.float64),
        "sizes": np.full(n, default_size, dtype=np.float64),
    }

    # Entry signals
    if entry_column in data.columns:
        entry_vals = data[entry_column].fillna(0).values
        result["entry_signals"] = entry_vals.astype(np.int8)

    # Exit signals
    if exit_column in data.columns:
        exit_vals = data[exit_column].fillna(0).values
        result["exit_signals"] = exit_vals.astype(np.int8)

    # Stop losses
    if sl_column and sl_column in data.columns:
        sl_vals = data[sl_column].fillna(0).values
        result["stop_losses"] = sl_vals.astype(np.float64)

    # Take profits
    if tp_column and tp_column in data.columns:
        tp_vals = data[tp_column].fillna(0).values
        result["take_profits"] = tp_vals.astype(np.float64)

    # Position sizes
    if size_column and size_column in data.columns:
        size_vals = data[size_column].fillna(default_size).values
        result["sizes"] = size_vals.astype(np.float64)

    return result


def prepare_signals_from_list(
    signals: List[Dict[str, Any]],
    n_bars: int,
    default_size: float = 0.1,
) -> Dict[str, np.ndarray]:
    """
    Convert list of signal dictionaries to NumPy arrays.

    Handles the event-driven signal format where each signal is a dict:
    {
        "bar_index": int,
        "entry_signal": int,  # 1=buy, -1=sell
        "exit_signal": int,   # 1=exit_long, -1=exit_short
        "sl": float,          # optional
        "tp": float,          # optional
        "size": float,        # optional
    }

    Args:
        signals: List of signal dictionaries
        n_bars: Total number of bars
        default_size: Default position size

    Returns:
        dict with NumPy arrays
    """
    result = {
        "entry_signals": np.zeros(n_bars, dtype=np.int8),
        "exit_signals": np.zeros(n_bars, dtype=np.int8),
        "stop_losses": np.zeros(n_bars, dtype=np.float64),
        "take_profits": np.zeros(n_bars, dtype=np.float64),
        "sizes": np.full(n_bars, default_size, dtype=np.float64),
    }

    for sig in signals:
        bar_idx = sig.get("bar_index", -1)
        if bar_idx < 0 or bar_idx >= n_bars:
            continue

        # Entry signal
        entry = sig.get("entry_signal", 0)
        if entry != 0:
            result["entry_signals"][bar_idx] = entry

        # Exit signal
        exit_sig = sig.get("exit_signal", 0)
        if exit_sig != 0:
            result["exit_signals"][bar_idx] = exit_sig

        # SL/TP
        sl = sig.get("sl", 0)
        if sl and sl > 0:
            result["stop_losses"][bar_idx] = sl

        tp = sig.get("tp", 0)
        if tp and tp > 0:
            result["take_profits"][bar_idx] = tp

        # Size
        size = sig.get("size", 0)
        if size and size > 0:
            result["sizes"][bar_idx] = size

    return result


def extract_ohlc_arrays(data: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Extract OHLC arrays from DataFrame.

    Args:
        data: DataFrame with OHLCV columns

    Returns:
        dict with opens, highs, lows, closes arrays
    """
    return {
        "opens": data["open"].values.astype(np.float64),
        "highs": data["high"].values.astype(np.float64),
        "lows": data["low"].values.astype(np.float64),
        "closes": data["close"].values.astype(np.float64),
    }


def prepare_simulation_inputs(
    data: pd.DataFrame,
    entry_column: str = "entry_signal",
    exit_column: str = "exit_signal",
    sl_column: Optional[str] = "sl",
    tp_column: Optional[str] = "tp",
    size_column: Optional[str] = "size",
    default_size: float = 0.1,
) -> Dict[str, np.ndarray]:
    """
    Prepare all inputs needed for run_simulation().

    Combines OHLC extraction and signal preparation into a single call.

    Args:
        data: DataFrame with OHLCV and signal columns
        entry_column: Column name for entry signals
        exit_column: Column name for exit signals
        sl_column: Column name for stop loss prices
        tp_column: Column name for take profit prices
        size_column: Column name for position sizes
        default_size: Default position size

    Returns:
        dict with all arrays needed for run_simulation():
            - opens, highs, lows, closes
            - entry_signals, exit_signals
            - stop_losses, take_profits, sizes
    """
    # Extract OHLC
    ohlc = extract_ohlc_arrays(data)

    # Extract signals
    signals = prepare_signals_from_dataframe(
        data=data,
        entry_column=entry_column,
        exit_column=exit_column,
        sl_column=sl_column,
        tp_column=tp_column,
        size_column=size_column,
        default_size=default_size,
    )

    return {**ohlc, **signals}

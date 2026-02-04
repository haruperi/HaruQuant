"""Numba-accelerated helpers for simulation hot loops."""

from __future__ import annotations

from typing import Callable

import numpy as np

try:
    from numba import njit as _njit

    NUMBA_AVAILABLE = True
except Exception:
    _njit = None
    NUMBA_AVAILABLE = False


def _no_jit(*_args, **_kwargs):
    def wrapper(func: Callable) -> Callable:
        return func

    return wrapper


_jit = _njit if NUMBA_AVAILABLE else _no_jit


@_jit(cache=True)
def numba_position_update(  # noqa: C901
    current_prices: np.ndarray,
    price_open: np.ndarray,
    volume: np.ndarray,
    direction: np.ndarray,
    sl: np.ndarray,
    tp: np.ndarray,
    valid: np.ndarray,
    contract_size: np.ndarray,
    tick_size: np.ndarray,
    tick_value: np.ndarray,
    margin_mode: np.ndarray,
    leverage: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute profit/margin arrays and SL/TP hits in a JIT-friendly loop."""
    count = current_prices.shape[0]
    profit = np.zeros(count, dtype=np.float64)
    margin = np.zeros(count, dtype=np.float64)
    sl_hit = np.zeros(count, dtype=np.bool_)
    tp_hit = np.zeros(count, dtype=np.bool_)

    for i in range(count):
        if not valid[i]:
            continue

        direction_val = direction[i]
        price_delta = (current_prices[i] - price_open[i]) * direction_val
        ts = tick_size[i]
        tv = tick_value[i]
        cs = contract_size[i]

        if ts > 0.0 and tv > 0.0:
            profit[i] = (price_delta / ts) * tv * volume[i]
        elif cs > 0.0:
            profit[i] = price_delta * cs * volume[i]

        mm = margin_mode[i]
        lv = leverage[i] if leverage[i] > 0.0 else 1.0
        if mm == 0.0:
            margin[i] = (volume[i] * cs) / lv
        elif mm == 1.0:
            margin[i] = volume[i] * cs
        elif mm == 2.0:
            margin[i] = volume[i] * cs * price_open[i]
        elif mm == 3.0:
            margin[i] = (volume[i] * cs * price_open[i]) / lv
        elif mm == 4.0:
            if ts > 0.0:
                margin[i] = volume[i] * cs * price_open[i] * tv / ts
        elif mm == 5.0 or mm == 6.0:
            margin[i] = volume[i] * cs * price_open[i]

        sl_val = sl[i]
        if sl_val != 0.0:
            if direction_val > 0:
                if current_prices[i] <= sl_val:
                    sl_hit[i] = True
            else:
                if current_prices[i] >= sl_val:
                    sl_hit[i] = True

        tp_val = tp[i]
        if tp_val != 0.0:
            if direction_val > 0:
                if current_prices[i] >= tp_val:
                    tp_hit[i] = True
            else:
                if current_prices[i] <= tp_val:
                    tp_hit[i] = True

    return profit, margin, sl_hit, tp_hit

"""Array-backed position state used by the simulator hot loop."""

from __future__ import annotations

from typing import Any, Callable, Optional

import numpy as np

from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


class PositionArrayState:
    """Maintain a struct-of-arrays mirror of open positions."""

    def __init__(self, initial_size: int = 16) -> None:
        """Initialize the position arrays with an optional initial capacity."""
        self._capacity = max(int(initial_size), 1)
        self.count = 0
        self.id_to_index: dict[int, int] = {}
        self.pos_id = np.zeros(self._capacity, dtype=np.int64)
        self.direction = np.zeros(self._capacity, dtype=np.int8)
        self.volume = np.zeros(self._capacity, dtype=np.float64)
        self.price_open = np.zeros(self._capacity, dtype=np.float64)
        self.price_current = np.zeros(self._capacity, dtype=np.float64)
        self.sl = np.zeros(self._capacity, dtype=np.float64)
        self.tp = np.zeros(self._capacity, dtype=np.float64)
        self.profit = np.zeros(self._capacity, dtype=np.float64)
        self.margin_required = np.zeros(self._capacity, dtype=np.float64)
        self.commission = np.zeros(self._capacity, dtype=np.float64)
        self.fee = np.zeros(self._capacity, dtype=np.float64)
        self.swap = np.zeros(self._capacity, dtype=np.float64)
        self.contract_size = np.zeros(self._capacity, dtype=np.float64)
        self.tick_size = np.zeros(self._capacity, dtype=np.float64)
        self.tick_value = np.zeros(self._capacity, dtype=np.float64)
        self.margin_mode = np.zeros(self._capacity, dtype=np.float64)
        self.leverage = np.zeros(self._capacity, dtype=np.float64)
        self.symbols: list[str] = [""] * self._capacity
        self.comments: list[str] = [""] * self._capacity
        self.open_time: list[object] = [None] * self._capacity
        self.pos_objects: list[Any] = [None] * self._capacity

    def _ensure_capacity(self, needed: int) -> None:
        if needed <= self._capacity:
            return
        new_cap = max(needed, self._capacity * 2)
        self.pos_id = self._grow(self.pos_id, new_cap)
        self.direction = self._grow(self.direction, new_cap)
        self.volume = self._grow(self.volume, new_cap)
        self.price_open = self._grow(self.price_open, new_cap)
        self.price_current = self._grow(self.price_current, new_cap)
        self.sl = self._grow(self.sl, new_cap)
        self.tp = self._grow(self.tp, new_cap)
        self.profit = self._grow(self.profit, new_cap)
        self.margin_required = self._grow(self.margin_required, new_cap)
        self.commission = self._grow(self.commission, new_cap)
        self.fee = self._grow(self.fee, new_cap)
        self.swap = self._grow(self.swap, new_cap)
        self.contract_size = self._grow(self.contract_size, new_cap)
        self.tick_size = self._grow(self.tick_size, new_cap)
        self.tick_value = self._grow(self.tick_value, new_cap)
        self.margin_mode = self._grow(self.margin_mode, new_cap)
        self.leverage = self._grow(self.leverage, new_cap)
        self.symbols.extend([""] * (new_cap - self._capacity))
        self.comments.extend([""] * (new_cap - self._capacity))
        self.open_time.extend([None] * (new_cap - self._capacity))
        self.pos_objects.extend([None] * (new_cap - self._capacity))
        self._capacity = new_cap

    @staticmethod
    def _grow(arr: np.ndarray, new_cap: int) -> np.ndarray:
        new_arr = np.zeros(new_cap, dtype=arr.dtype)
        new_arr[: arr.shape[0]] = arr
        return new_arr

    def clear(self) -> None:
        """Reset the arrays to an empty state."""
        self.count = 0
        self.id_to_index.clear()

    def add_or_update(
        self,
        pos_id: int,
        pos_data: Any,
        symbol_params: Optional[dict[str, float]] = None,
        leverage: Optional[float] = None,
    ) -> None:
        """Insert or update a position row in the arrays."""
        idx = self.id_to_index.get(int(pos_id))
        if idx is None:
            idx = self.count
            self._ensure_capacity(idx + 1)
            self.count += 1
            self.id_to_index[int(pos_id)] = idx
        self.pos_id[idx] = int(pos_id)
        pos_type = getattr(pos_data, "type", 0)
        if pos_type == mt5.POSITION_TYPE_BUY or pos_type == mt5.ORDER_TYPE_BUY:
            self.direction[idx] = 1
        else:
            self.direction[idx] = -1
        self.volume[idx] = float(getattr(pos_data, "volume", 0.0) or 0.0)
        self.price_open[idx] = float(getattr(pos_data, "price_open", 0.0) or 0.0)
        self.price_current[idx] = float(
            getattr(pos_data, "price_current", self.price_open[idx]) or 0.0
        )
        self.sl[idx] = float(getattr(pos_data, "sl", 0.0) or 0.0)
        self.tp[idx] = float(getattr(pos_data, "tp", 0.0) or 0.0)
        self.profit[idx] = float(getattr(pos_data, "profit", 0.0) or 0.0)
        self.margin_required[idx] = float(
            getattr(pos_data, "margin_required", 0.0) or 0.0
        )
        self.commission[idx] = float(getattr(pos_data, "commission", 0.0) or 0.0)
        self.fee[idx] = float(getattr(pos_data, "fee", 0.0) or 0.0)
        self.swap[idx] = float(getattr(pos_data, "swap", 0.0) or 0.0)
        self.symbols[idx] = str(getattr(pos_data, "symbol", "") or "")
        self.comments[idx] = str(getattr(pos_data, "comment", "") or "")
        self.open_time[idx] = getattr(pos_data, "time", None)
        self.pos_objects[idx] = pos_data

        if symbol_params is not None:
            self.contract_size[idx] = float(symbol_params.get("contract_size", 0.0))
            self.tick_size[idx] = float(symbol_params.get("tick_size", 0.0))
            self.tick_value[idx] = float(symbol_params.get("tick_value", 0.0))
            self.margin_mode[idx] = float(symbol_params.get("margin_mode", 0.0))
            if leverage is None:
                self.leverage[idx] = float(symbol_params.get("leverage", 1.0))
            else:
                self.leverage[idx] = float(leverage)
        elif leverage is not None:
            self.leverage[idx] = float(leverage)

    def remove(self, pos_id: int) -> None:
        """Remove a position row by id, keeping arrays compact."""
        idx = self.id_to_index.pop(int(pos_id), None)
        if idx is None:
            return
        last = self.count - 1
        if idx != last:
            self._swap(idx, last)
            moved_id = int(self.pos_id[idx])
            self.id_to_index[moved_id] = idx
        self.count -= 1

    def _swap(self, i: int, j: int) -> None:
        for arr in (
            self.pos_id,
            self.direction,
            self.volume,
            self.price_open,
            self.price_current,
            self.sl,
            self.tp,
            self.profit,
            self.margin_required,
            self.commission,
            self.fee,
            self.swap,
            self.contract_size,
            self.tick_size,
            self.tick_value,
            self.margin_mode,
            self.leverage,
        ):
            arr[i], arr[j] = arr[j], arr[i]
        self.symbols[i], self.symbols[j] = self.symbols[j], self.symbols[i]
        self.comments[i], self.comments[j] = self.comments[j], self.comments[i]
        self.open_time[i], self.open_time[j] = self.open_time[j], self.open_time[i]
        self.pos_objects[i], self.pos_objects[j] = (
            self.pos_objects[j],
            self.pos_objects[i],
        )

    def update_sl_tp(self, pos_id: int, sl: float, tp: float) -> None:
        """Update SL/TP values for a position row."""
        idx = self.id_to_index.get(int(pos_id))
        if idx is None:
            return
        self.sl[idx] = float(sl or 0.0)
        self.tp[idx] = float(tp or 0.0)

    def update_volume_margin(self, pos_id: int, volume: float, margin: float) -> None:
        """Update volume and margin fields for a position row."""
        idx = self.id_to_index.get(int(pos_id))
        if idx is None:
            return
        self.volume[idx] = float(volume or 0.0)
        self.margin_required[idx] = float(margin or 0.0)

    def rebuild_from_positions(
        self,
        positions: dict[int, Any],
        get_symbol_params: Optional[Callable[[str], Optional[dict[str, float]]]] = None,
        leverage: Optional[float] = None,
    ) -> None:
        """Rebuild the arrays from the current positions dict."""
        self.clear()
        for pos_id, pos_data in positions.items():
            params = None
            if get_symbol_params is not None:
                params = get_symbol_params(str(getattr(pos_data, "symbol", "") or ""))
            self.add_or_update(
                pos_id=pos_id,
                pos_data=pos_data,
                symbol_params=params,
                leverage=leverage,
            )

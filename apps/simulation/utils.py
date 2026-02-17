"""
Simulation helper utilities.

This module provides helper methods and mixins for the Trading Simulator,
handling calculations, data normalization, state updates, and performance optimizations.

Classes:
    PositionArrayState: Struct-of-arrays for efficient position tracking.
    SimulatorBacktestResult: Backtest result wrapper for the simulator.
    SimulationUtilsMixin: Helper methods used by the TradeSimulator.

Functions:
    numba_position_update: JIT-compiled position profit/margin calculations.

SimulationUtilsMixin Methods:
    Data Normalization:
        _normalize_pending_type: Normalize order type strings.
        _normalize_expiry_date: Ensure expiry dates are in UTC.

    Validation & Processing:
        _validate_pending_distance: Enforce minimum distance for pending orders.

    State Updates:
        _update_position_entry: Record open position details.
        _ensure_trade_record: Maintain trade records for reporting.

    Database:
        _save_backtest_to_db: Persist results to the database.

"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

import numpy as np

from apps.utils.logger import logger
from apps.mt5 import get_mt5_api
from apps.sqlite.backtests import BacktestManager
from apps.sqlite.database_operations import DatabaseManager
from apps.trade import PositionInfo

mt5 = get_mt5_api()

# =============================================================================
# Numba JIT Compilation Support
# =============================================================================

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
    """Compute profit/margin arrays and SL/TP hits in a JIT-friendly loop.

    This function is JIT-compiled with Numba for performance when available.
    Falls back to pure Python implementation when Numba is not installed.

    Args:
        current_prices: Current market prices for each position
        price_open: Opening prices for each position
        volume: Position volumes
        direction: Position directions (1 for buy, -1 for sell)
        sl: Stop loss prices
        tp: Take profit prices
        valid: Boolean mask of valid positions
        contract_size: Contract sizes for each symbol
        tick_size: Tick sizes for each symbol
        tick_value: Tick values for each symbol
        margin_mode: Margin calculation modes
        leverage: Leverage values

    Returns:
        Tuple of (profit, margin, sl_hit, tp_hit) arrays
    """
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


# =============================================================================
# Position Array State (Struct-of-Arrays Pattern)
# =============================================================================


class PositionArrayState:
    """Maintain a struct-of-arrays mirror of open positions.

    This class uses the struct-of-arrays pattern for efficient position tracking
    in the simulation hot loop. All position data is stored in contiguous NumPy
    arrays for cache-friendly access and potential vectorization.
    """

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


# =============================================================================
# Backtest Result Wrapper
# =============================================================================


class SimulatorBacktestResult:
    """Backtest result wrapper for simulator to match old BacktestResult interface."""

    def __init__(self, simulator):
        """Initialize from simulator instance."""
        self.simulator = simulator
        self.trades = simulator._completed_trades
        self.initial_balance = simulator._initial_balance
        self.final_balance = simulator._account_data.balance
        self.total_return = self.final_balance - self.initial_balance
        self.total_return_pct = (
            ((self.final_balance - self.initial_balance) / self.initial_balance) * 100
            if self.initial_balance > 0
            else 0.0
        )

        # Get start and end dates from trades or simulator
        if self.trades:
            self.start_date = self.trades[0].open_time
            self.end_date = self.trades[-1].close_time
        else:
            # Fallback to current time
            from datetime import datetime

            self.start_date = datetime.now()
            self.end_date = datetime.now()

        # Calculate trade statistics
        if self.trades:
            winning_trades = [t for t in self.trades if t.profit_loss > 0]
            losing_trades = [t for t in self.trades if t.profit_loss < 0]
            breakeven_trades = [t for t in self.trades if t.profit_loss == 0]

            self.total_trades = len(self.trades)
            self.winning_trades = len(winning_trades)
            self.losing_trades = len(losing_trades)
            self.breakeven_trades = len(breakeven_trades)
            self.win_rate = (
                (self.winning_trades / self.total_trades) * 100
                if self.total_trades > 0
                else 0.0
            )

            self.gross_profit = sum(t.profit_loss for t in winning_trades)
            self.gross_loss = abs(sum(t.profit_loss for t in losing_trades))
            self.profit_factor = (
                self.gross_profit / self.gross_loss
                if self.gross_loss > 0
                else float("inf")
            )

            # Average win/loss
            self.avg_win = (
                self.gross_profit / len(winning_trades) if winning_trades else 0.0
            )
            self.avg_loss = (
                self.gross_loss / len(losing_trades) if losing_trades else 0.0
            )

            # Expectancy
            self.expectancy = (self.win_rate / 100 * self.avg_win) - (
                (100 - self.win_rate) / 100 * self.avg_loss
            )

            # Calculate drawdown (in dollars and percentage)
            equity_curve = [self.initial_balance]
            running_balance = self.initial_balance
            for trade in self.trades:
                running_balance += trade.profit_loss
                equity_curve.append(running_balance)

            peak = equity_curve[0]
            max_dd_dollars = 0.0
            max_dd_pct = 0.0
            for equity in equity_curve:
                if equity > peak:
                    peak = equity
                dd_dollars = peak - equity
                dd_pct = ((peak - equity) / peak) * 100 if peak > 0 else 0.0
                if dd_dollars > max_dd_dollars:
                    max_dd_dollars = dd_dollars
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

            self.max_drawdown = max_dd_dollars
            self.max_drawdown_pct = max_dd_pct
        else:
            self.total_trades = 0
            self.winning_trades = 0
            self.losing_trades = 0
            self.breakeven_trades = 0
            self.win_rate = 0.0
            self.gross_profit = 0.0
            self.gross_loss = 0.0
            self.profit_factor = 0.0
            self.avg_win = 0.0
            self.avg_loss = 0.0
            self.expectancy = 0.0
            self.max_drawdown = 0.0
            self.max_drawdown_pct = 0.0

        # Calculate Sharpe ratio (simplified version)
        if self.trades and len(self.trades) > 1:
            import numpy as np

            returns = [t.profit_loss / self.initial_balance for t in self.trades]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            self.sharpe_ratio = (
                (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
            )
        else:
            self.sharpe_ratio = 0.0

    def summary(self):
        """Return summary metrics dictionary."""
        return {
            "total_return_pct": self.total_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate_pct": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
        }

    def _get_equity_series(self):
        """Get equity curve as pandas Series."""
        import pandas as pd

        if not self.trades:
            return pd.Series([self.initial_balance])

        # Build equity curve from trades
        equity_curve = [self.initial_balance]
        running_balance = self.initial_balance
        timestamps = [self.trades[0].open_time]

        for trade in self.trades:
            running_balance += trade.profit_loss
            equity_curve.append(running_balance)
            timestamps.append(trade.close_time)

        return pd.Series(equity_curve, index=timestamps)

    def _get_returns_series(self):
        """Get returns series as pandas Series."""
        import pandas as pd

        equity_series = self._get_equity_series()
        if len(equity_series) <= 1:
            return pd.Series([])

        # Calculate percentage returns
        returns = equity_series.pct_change().dropna()
        return returns * 100  # Return as percentage

    def get_trades_df(self):
        """Get trades as pandas DataFrame."""
        import pandas as pd

        if not self.trades:
            return pd.DataFrame()

        # Convert trades to list of dicts
        trades_data = []
        for trade in self.trades:
            trade_dict = {
                "type": "BUY" if trade.type == 0 else "SELL",
                "open_time": trade.open_time,
                "close_time": trade.close_time,
                "open_price": trade.open_price,
                "close_price": trade.close_price,
                "size": trade.size,
                "commission": trade.commission,
                "swap": trade.swap,
                "profit_loss": trade.profit_loss,
                "profit_loss_pips": trade.profit_loss_pips,
                "time_in_trade_formatted": f"{int((trade.close_time - trade.open_time).total_seconds() / 3600)}h",
            }
            trades_data.append(trade_dict)

        return pd.DataFrame(trades_data)


def calculate_metrics_from_simulator(simulator):
    """
    Create a BacktestResult-like object from simulator state.

    Args:
        simulator: TradeSimulator instance

    Returns:
        SimulatorBacktestResult with metrics and summary() method
    """
    return SimulatorBacktestResult(simulator)


class SimulationUtilsMixin:
    """Helper methods used by the TradeSimulator."""

    _symbols_data: dict[str, Any]
    _ticks_data: dict[str, Any]
    _positions_data: dict[int, Any]
    _simulator: Any
    trade: Any
    _account_data: Any
    _completed_trades: list[Any]
    _initial_balance: float
    _to_epoch_seconds: Callable[..., int]
    close_position: Callable[..., Any]

    # Calculations

    def _sl_tp_from_pips(
        self,
        action: str,
        symbol: str,
        entry_price: float,
        sl_pips: float,
        tp_pips: float,
    ) -> tuple[float, float]:
        symbol_info = self._symbols_data.get(symbol)
        point = symbol_info.point if symbol_info is not None else 0.00001
        pip_size = point * 10

        sl_price = 0.0
        tp_price = 0.0
        if sl_pips:
            sl_offset = float(sl_pips) * pip_size
            sl_price = (
                entry_price - sl_offset if action == "buy" else entry_price + sl_offset
            )
        if tp_pips:
            tp_offset = float(tp_pips) * pip_size
            tp_price = (
                entry_price + tp_offset if action == "buy" else entry_price - tp_offset
            )
        return sl_price, tp_price

    def _update_position_entry(
        self,
        action: str,
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        comment: str,
        margin_required: float,
        open_time: object,
        pos_id: Optional[int] = None,
    ) -> None:
        if open_time is None:
            logger.error("open_time is required to record position entry time")
            return
        if pos_id is None:
            pos_info = PositionInfo(api=self._simulator)
            if not pos_info.Select(symbol):
                return
            pos_id = pos_info.Identifier()
        pos_data = self._positions_data.get(int(pos_id))
        if pos_data is None:
            return

        now = self._to_epoch_seconds(open_time)
        pos_type = mt5.POSITION_TYPE_BUY if action == "buy" else mt5.POSITION_TYPE_SELL
        pos_data.time = now
        pos_data.time_msc = now * 1000
        pos_data.time_update = now
        pos_data.time_update_msc = now * 1000
        pos_data.identifier = pos_id
        pos_data.magic = int(self.trade.RequestMagic())
        pos_data.symbol = symbol
        pos_data.type = int(pos_type)
        pos_data.volume = float(volume)
        pos_data.price_open = float(price)
        pos_data.price_current = float(price)
        pos_data.sl = float(sl)
        pos_data.tp = float(tp)
        pos_data.swap = 0.0
        pos_data.profit = 0.0
        pos_data.comment = comment
        pos_data.margin_required = float(margin_required)
        if hasattr(pos_data, "commission"):
            pos_data.commission = 0.0
        if hasattr(pos_data, "fee"):
            pos_data.fee = 0.0

        position_state = getattr(self, "_position_array_state", None)
        if position_state is not None:
            symbol_params = None
            get_params = getattr(self, "_get_symbol_calc_params", None)
            if callable(get_params):
                symbol_params = get_params(symbol)
            leverage = getattr(self._account_data, "leverage", None)
            position_state.add_or_update(
                pos_id=int(pos_id),
                pos_data=pos_data,
                symbol_params=symbol_params,
                leverage=leverage,
            )

    # Data Normalization
    def _normalize_pending_type(self, order_type: object) -> str:
        if isinstance(order_type, int):
            mapping = {
                mt5.ORDER_TYPE_BUY_LIMIT: "buy limit",
                mt5.ORDER_TYPE_SELL_LIMIT: "sell limit",
                mt5.ORDER_TYPE_BUY_STOP: "buy stop",
                mt5.ORDER_TYPE_SELL_STOP: "sell stop",
                mt5.ORDER_TYPE_BUY_STOP_LIMIT: "buy stop limit",
                mt5.ORDER_TYPE_SELL_STOP_LIMIT: "sell stop limit",
            }
            return mapping.get(order_type, "")
        if hasattr(order_type, "value"):
            try:
                return self._normalize_pending_type(int(order_type.value))
            except Exception:
                return ""
        if not isinstance(order_type, str):
            return ""
        return order_type.strip().lower().replace("_", " ")

    def _pending_type_enum_name(self, order_type: str) -> str:
        mapping = {
            "buy limit": "BUY_LIMIT",
            "sell limit": "SELL_LIMIT",
            "buy stop": "BUY_STOP",
            "sell stop": "SELL_STOP",
            "buy stop limit": "BUY_STOP_LIMIT",
            "sell stop limit": "SELL_STOP_LIMIT",
        }
        return mapping.get(self._normalize_pending_type(order_type), "")

    def _pending_action(self, order_type: str) -> str:
        normalized = self._normalize_pending_type(order_type)
        return "buy" if normalized.startswith("buy") else "sell"

    def _normalize_expiry_date(
        self, expiry_date: Optional[datetime]
    ) -> Optional[datetime]:
        if expiry_date is None:
            return None
        if getattr(expiry_date, "tzinfo", None) is not None:
            return expiry_date.astimezone(timezone.utc).replace(tzinfo=None)
        return expiry_date

    # Validation & Processing
    def _validate_pending_distance(
        self,
        order_type: str,
        symbol: str,
        open_price: float,
    ) -> tuple[bool, str]:
        symbol_info = self._symbols_data.get(symbol)
        tick = self._ticks_data.get(symbol)
        if symbol_info is None or tick is None:
            return False, "Symbol info or tick data not available"

        stop_distance = float(symbol_info.trade_stops_level or 0) * float(
            symbol_info.point or 0.0
        )
        if stop_distance <= 0:
            return True, "OK"

        bid = float(tick.bid or 0.0)
        ask = float(tick.ask or 0.0)
        normalized = self._normalize_pending_type(order_type)
        if normalized.startswith("buy"):
            if abs(open_price - bid) < stop_distance:
                return False, "Pending BUY order too close to bid"
        else:
            if abs(open_price - ask) < stop_distance:
                return False, "Pending SELL order too close to ask"
        return True, "OK"

    # Database Operations
    def _save_backtest_to_db(self, metadata: Optional[dict]) -> None:
        """Persist completed trades and run metadata into the backtest tables.

        Uses BacktestManager for all database operations to maintain consistency
        and proper separation of concerns.
        """
        if not metadata:
            logger.error("save_db=True but metadata is missing")
            return

        required = [
            "strategy_name",
            "strategy_version",
            "start_date",
            "end_date",
            "engine_type",
            "data_resolution",
            "config_hash",
        ]
        missing = [key for key in required if key not in metadata]
        if missing:
            logger.error(f"Missing required metadata keys: {', '.join(missing)}")
            return

        try:
            # Initialize BacktestManager with database path
            db_manager = DatabaseManager()
            backtest_manager = BacktestManager()
            backtest_manager.db_path = db_manager.db_path

            # Convert pandas timestamps to datetime if needed
            start_date = metadata["start_date"]
            if hasattr(start_date, "to_pydatetime"):
                start_date = start_date.to_pydatetime()
            end_date = metadata["end_date"]
            if hasattr(end_date, "to_pydatetime"):
                end_date = end_date.to_pydatetime()

            # Step 1: Create backtest run in backtest_runs table
            backtest_id = backtest_manager.create_backtest_run(
                strategy_name=metadata["strategy_name"],
                strategy_version=metadata["strategy_version"],
                start_date=start_date,
                end_date=end_date,
                engine_type=metadata["engine_type"],
                data_resolution=metadata["data_resolution"],
                config_hash=metadata["config_hash"],
                strategy_version_id=metadata.get("strategy_version_id"),
                user_id=metadata.get("user_id"),
                symbols=metadata.get("symbols"),
                timeframes=metadata.get("timeframes"),
                initial_balance=float(
                    metadata.get("initial_balance", self._initial_balance)
                ),
                alias=metadata.get("alias"),
                description=metadata.get("description"),
                commission_model=metadata.get("commission_model"),
                slippage_model=metadata.get("slippage_model"),
                spread_model=metadata.get("spread_model"),
                execution_model=metadata.get("execution_model"),
                fill_model=metadata.get("fill_model"),
                risk_model=metadata.get("risk_model"),
                position_sizing_model=metadata.get("position_sizing_model"),
            )

            # Step 2: Save trades to backtest_trades table
            if self._completed_trades:
                backtest_manager.save_backtest_trades(
                    backtest_id=backtest_id, trades=self._completed_trades
                )
                logger.info(f"Saved {len(self._completed_trades)} trades to database")

            # Step 3: Update final balance and status
            final_balance = float(self._account_data.balance)
            backtest_manager.update_backtest_status(
                backtest_id=backtest_id, status="completed", final_balance=final_balance
            )

            logger.info(
                f"Backtest saved successfully (ID: {backtest_id}, "
                f"Final Balance: {final_balance:.2f})"
            )

        except Exception as exc:
            logger.error(f"Failed to save backtest results: {exc}")
            raise


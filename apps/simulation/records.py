"""
Trade record structures and tracking helpers for the simulator.

This module defines the data structures for capturing trade lifecycles and provides
mixins for managing trade records during simulation.

Classes:
    TradeRecord: Dataclass for storing the full lifecycle and performance of a trade.
    TradeRecordMixin: Helper methods for initializing and updating trade records.

TradeRecordMixin Methods:
    Time & Conversion:
        _to_epoch_seconds: Convert datetime/object to Unix timestamp.
        _to_datetime: Convert timestamp/object to datetime object.
        _current_sim_time: Get the current simulation wall time.

    Data Calculation:
        _pip_size: Calculate the pip size for a given symbol.

    Record Management:
        _ensure_trade_record: Create a new TradeRecord for a position if one doesn't exist.
        _update_trade_tracker: Update MFE/MAE and bar count for an open position.

"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class TradeRecord:
    """
    Record of a completed trade.

    Captures the full trade lifecycle from entry to exit.
    Fields are aligned to backtest_trades for database storage.
    """

    # 1. Trade Identification and Attribution
    trade_id: Optional[str] = None
    ticket: int = 0
    symbol: str = ""
    type: str = "buy"
    magic_number: int = 0
    strategy_name: Optional[str] = None
    setup: Optional[str] = None
    sample_type: Optional[str] = None
    comment: str = ""

    # 2. Strategy Context
    signal_timeframe: Optional[str] = None
    execution_timeframe: Optional[str] = None
    session: Optional[str] = None
    day_of_week: Optional[int] = None
    hour_of_day: Optional[int] = None

    # 3. Trade Timing
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    time_in_trade: float = 0.0  # Seconds
    bars_in_trade: int = 0

    # 4. Entry Definition
    open_price: float = 0.0
    orig_open_price: Optional[float] = None
    orig_open_time: Optional[datetime] = None
    requested_entry_price: float = 0.0
    spread_at_entry: float = 0.0
    atr_at_entry: Optional[float] = None
    size: float = 0.0

    # 5. Exit Definition
    close_price: float = 0.0
    requested_exit_price: float = 0.0
    close_type: str = "UNKNOWN"
    exit_reason: str = "UNKNOWN"

    # 6. Trade Plan and Risk
    stop_loss_price: float = 0.0
    profit_target_price: float = 0.0
    initial_risk_pips: float = 0.0
    initial_risk_usd: float = 0.0

    # 7. Account State
    balance_at_entry: float = 0.0
    equity_at_entry: float = 0.0
    margin_used: float = 0.0
    free_margin: float = 0.0
    balance_pips: float = 0.0

    # 8. Trade Management
    max_position_size: float = 0.0
    partial_close_count: int = 0
    trailing_stop_used: bool = False
    breakeven_triggered: bool = False

    # 9. Execution Quality
    slippage_usd: float = 0.0
    fill_price_deviation: float = 0.0
    execution_latency_ms: float = 0.0

    # 10. Performance Results
    profit_loss: float = 0.0
    profit_loss_pips: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    r_multiple: float = 0.0
    buy_hold: float = 0.0
    buy_hold_pips: float = 0.0

    # 11. Excursion and Drawdown Analytics
    mae_usd: float = 0.0
    mae_pips: float = 0.0
    mfe_usd: float = 0.0
    mfe_pips: float = 0.0
    drawdown: float = 0.0

    # 12. Regime and Research Tags
    market_regime: Optional[str] = None
    volatility_bucket: Optional[str] = None
    correlation_cluster: Optional[str] = None

    # 13. Compliance and Audit
    rule_violation: bool = False
    manual_intervention: bool = False


class TradeRecordMixin:
    """Helper methods for trade record tracking."""

    _symbols_data: dict[str, Any]
    _trade_records_open: dict[int, TradeRecord]
    _ticks_data: dict[str, Any]
    _trade_trackers: dict[int, dict[str, Any]]
    trade: Any
    _account_data: Any
    mt5_client: Any

    # Time & Conversion Helpers
    def _to_epoch_seconds(self, value: Optional[object]) -> int:
        if value is None:
            return int(time.time())
        if isinstance(value, (int, float)):
            return int(value)
        if hasattr(value, "timestamp"):
            return int(value.timestamp())
        return int(time.time())

    def _to_datetime(self, value: Optional[object]) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value))
        if hasattr(value, "timestamp"):
            return datetime.fromtimestamp(int(value.timestamp()))
        return datetime.utcnow()

    def _current_sim_time(self) -> datetime:
        if hasattr(self, "_current_time") and isinstance(self._current_time, datetime):
            return self._current_time
        return datetime.utcnow()

    # Data Calculation
    def _pip_size(self, symbol: str) -> float:
        symbol_info = self._symbols_data.get(symbol)
        point = symbol_info.point if symbol_info is not None else 0.00001
        return float(point) * 10.0

    # Record Management
    def _ensure_trade_record(
        self,
        pos_id: int,
        action: str,
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        comment: str,
        requested_entry_price: float,
        open_time: object,
    ) -> None:
        if pos_id in self._trade_records_open:
            return

        tick = self._ticks_data.get(symbol)
        spread = 0.0
        if tick is not None:
            spread = float((tick.ask or 0.0) - (tick.bid or 0.0))
        pip_size = self._pip_size(symbol)
        spread_pips = float(spread / pip_size) if pip_size > 0 else 0.0

        open_dt = self._to_datetime(open_time)
        record = TradeRecord(
            trade_id=str(uuid.uuid4()),
            ticket=int(pos_id),
            symbol=symbol,
            type=action,
            magic_number=int(self.trade.RequestMagic()),
            comment=comment,
            open_time=open_dt,
            open_price=float(price),
            orig_open_price=float(price),
            orig_open_time=open_dt,
            requested_entry_price=float(requested_entry_price or price),
            spread_at_entry=spread_pips,
            size=float(volume),
            stop_loss_price=float(sl),
            profit_target_price=float(tp),
            balance_at_entry=float(self._account_data.balance),
            equity_at_entry=float(self._account_data.equity),
            margin_used=float(self._account_data.margin),
            free_margin=float(self._account_data.margin_free),
            max_position_size=float(volume),
        )

        if sl:
            if action == "buy":
                risk_pips = (record.open_price - sl) / pip_size if pip_size > 0 else 0.0
            else:
                risk_pips = (sl - record.open_price) / pip_size if pip_size > 0 else 0.0
            record.initial_risk_pips = float(max(risk_pips, 0.0))
            record.initial_risk_usd = float(
                abs(
                    self.mt5_client.order_calc_profit(
                        0 if action == "buy" else 1,
                        symbol,
                        record.size,
                        record.open_price,
                        float(sl),
                    )
                )
            )

        self._trade_records_open[pos_id] = record
        self._trade_trackers[pos_id] = {
            "bars_in_trade": 0,
            "mfe_usd": 0.0,
            "mae_usd": 0.0,
            "mfe_pips": 0.0,
            "mae_pips": 0.0,
        }

    def _update_trade_tracker(
        self,
        pos_id: int,
        action: str,
        symbol: str,
        entry_price: float,
        current_price: float,
        profit_usd: float,
    ) -> None:
        tracker = self._trade_trackers.get(pos_id)
        if tracker is None:
            return

        tracker["bars_in_trade"] += 1
        if profit_usd > tracker["mfe_usd"]:
            tracker["mfe_usd"] = float(profit_usd)
        if profit_usd < tracker["mae_usd"]:
            tracker["mae_usd"] = float(profit_usd)

        pip_size = self._pip_size(symbol)
        if pip_size > 0:
            if action == "buy":
                pips = (current_price - entry_price) / pip_size
            else:
                pips = (entry_price - current_price) / pip_size
            if pips > tracker["mfe_pips"]:
                tracker["mfe_pips"] = float(pips)
            if pips < tracker["mae_pips"]:
                tracker["mae_pips"] = float(pips)

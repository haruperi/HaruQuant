"""
Simulation helper utilities.

This module provides helper methods and mixins for the Trading Simulator,
handling calculations, data normalization, and state updates.

Classes:
    SimulationUtilsMixin: Helper methods used by the TradeSimulator.

SimulationUtilsMixin Methods:
    Data Normalization:
        _normalize_pending_type: Normalize order type strings.
        _normalize_expiry_date: Ensure expiry dates are in UTC.

    Validation & Processing:
        _validate_pending_distance: Enforce minimum distance for pending orders.

    State Updates:
        _update_position_entry: Record open position details.
        _ensure_trade_record: Maintain trade records for reporting.

    Database & Cleanup:
        close_all_positions: Bulk closure of open positions.
        _save_backtest_to_db: Persist results to the database.

"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from apps.logger import logger
from apps.mt5 import get_mt5_api
from apps.sqlite import SQLiteDatabase
from apps.trade import PositionInfo

mt5 = get_mt5_api()


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

    # State Updates & Cleanup
    def close_all_positions(self, reason: str = "Time exit") -> None:
        """Close all open positions using the latest tick data."""
        positions = self._simulator.positions_get() or []
        for position in positions:
            pos_data = (
                position._asdict() if hasattr(position, "_asdict") else dict(position)
            )
            self.close_position(pos_data, reason=reason)

    def _save_backtest_to_db(self, metadata: Optional[dict]) -> None:
        """Persist completed trades and run metadata into the backtest tables."""
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

        db = SQLiteDatabase()
        start_date = metadata["start_date"]
        if hasattr(start_date, "to_pydatetime"):
            start_date = start_date.to_pydatetime()
        end_date = metadata["end_date"]
        if hasattr(end_date, "to_pydatetime"):
            end_date = end_date.to_pydatetime()

        backtest_id = db.create_backtest_run(
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

        conn = sqlite3.connect(db.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            if self._completed_trades:
                db._save_trades(cursor, backtest_id, self._completed_trades)
            cursor.execute(
                """
                UPDATE backtest_runs
                SET final_balance = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE backtest_id = ?
                """,
                (float(self._account_data.balance), backtest_id),
            )
            conn.commit()
        except Exception as exc:
            logger.error(f"Failed to save backtest results: {exc}")
            conn.rollback()
        finally:
            conn.close()

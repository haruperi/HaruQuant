"""
Trading Simulator.

This module provides simulation capabilities for backtesting trading strategies
using the Trade module with simulated market data.

Classes:
    TradeSimulator: Trading Simulator for backtesting.

TradeSimulator Methods:
    Market Execution:
        open_position: Open a position via Trade using a buy/sell action string.
        close_position: Close a position via Trade using a buy/sell action string.

    Pending Orders:
        buy_limit, sell_limit: Place limit orders.
        buy_stop, sell_stop: Place stop orders.
        buy_stop_limit, sell_stop_limit: Place stop limit orders.

    Management:
        order_delete: Delete a pending order from the simulator.
        order_modify: Modify a pending order's price, SL/TP, or expiry.
        modify_position: Modify an open position's stop loss or take profit.

"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np

from apps.utils.logger import logger
from apps.mt5 import MT5Client, get_mt5_api
from apps.simulation.data import (
    AccountInfoSimulator,
    PositionInfoSimulator,
    TradeSimulator,
    SymbolInfoSimulator,
    SymbolTickSimulator,
)
from apps.simulation.engine import SimulationEngine
from apps.simulation.records import TradeRecord
from apps.simulation.utils import PositionArrayState, SimulationUtilsMixin
from apps.trade import AccountInfo, Trade
from apps.utils.validate import TradeValidator

mt5 = get_mt5_api()


class TradeSimulator(SimulationEngine, SimulationUtilsMixin):
    """
    Trading Simulator for backtesting.

    Simulates trading operations bar by bar using the Trade module.
    """

    def __init__(
        self,
        simulator_name: str,
        mt5_client: Optional[MT5Client],
        account_info: AccountInfoSimulator,
        symbols: Optional[dict[str, SymbolInfoSimulator]] = None,
    ) -> None:
        """
        Initialize the Trading Simulator.

        Args:
            simulator_name: Name of the simulation session
            mt5_client: Connected MT5Client instance for accurate calculations
            account_info: AccountInfoSimulator instance for accurate calculations
            symbols: Optional symbols to be added to the simulator
        """
        self.simulator_name = simulator_name
        self.mt5_client = mt5_client
        self._account_data = account_info

        symbols = symbols or {}
        self._symbols_data: dict[str, SymbolInfoSimulator] = symbols
        self._ticks_data: dict[str, SymbolTickSimulator] = {}
        self._positions_data: dict[int, PositionInfoSimulator] = {}
        self._trade_records_open: dict[int, TradeRecord] = {}
        self._trade_trackers: dict[int, dict] = {}
        self._completed_trades: list[TradeRecord] = []
        self._initial_balance = float(self._account_data.balance)
        self._position_array_state: PositionArrayState = PositionArrayState()

        # Create simulator client
        self._simulator = TradeSimulator(
            account_data=self._account_data,
            symbols_data=self._symbols_data,
            ticks_data=self._ticks_data,
            positions_data=self._positions_data,
            mt5_client=mt5_client,
        )
        self._simulator._position_array_state = self._position_array_state

        # Initialize Trade and info classes
        self.trade = Trade(api=self._simulator)
        self.account = AccountInfo(api=self._simulator)

        # Simulation state
        self._current_bar = 0

        logger.info(
            f"Initialized TradeSimulator: {simulator_name} Deposit: {self._account_data.balance}, Leverage: {self._account_data.leverage}"
        )

    # Market Execution
    def open_position(
        self,
        action: str,
        symbol: str,
        volume: float,
        price: float,
        open_time: object,
        sl_pips: float = 0.0,
        tp_pips: float = 0.0,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        comment: str = "",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """
        Open a position via Trade using a buy/sell action string.

        Returns True if the trade request succeeds.
        """
        if action not in ("buy", "sell"):
            logger.error(f"Unknown action: {action}")
            return False

        if getattr(self, "_log_trades", True):
            logger.info(f">>> Entering {action.upper()} position")

        if open_time is None:
            logger.error("open_time is required to record position entry time")
            return False

        if sl_pips < 0 or tp_pips < 0:
            logger.error("SL/TP pips must be non-negative")
            return False

        if self.mt5_client:
            margin_req = self.mt5_client.order_calc_margin(
                0 if action == "buy" else 1,
                symbol,
                volume,
                price,
            )
        else:
            margin_req = 0.0

        sl_price_calc, tp_price_calc = self._sl_tp_from_pips(
            action=action,
            symbol=symbol,
            entry_price=price,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
        )
        sl_price = float(sl_price if sl_price is not None else sl_price_calc)
        tp_price = float(tp_price if tp_price is not None else tp_price_calc)

        # Validation is handled inside simulator.order_send (MT5-like).

        if action == "buy":
            result = self.trade.Buy(
                volume=volume,
                symbol=symbol,
                price=price,
                sl=sl_price,
                tp=tp_price,
                comment=comment,
            )
        else:
            result = self.trade.Sell(
                volume=volume,
                symbol=symbol,
                price=price,
                sl=sl_price,
                tp=tp_price,
                comment=comment,
            )
        if result:
            if getattr(self, "_log_trades", True):
                logger.info(
                    f"{action.upper()} position opened successfully {self.trade.ResultOrder()}"
                )
            pos_id = self._simulator._next_position_id - 1
            self._update_position_entry(
                action=action,
                symbol=symbol,
                volume=volume,
                price=price,
                sl=sl_price,
                tp=tp_price,
                comment=comment,
                margin_required=margin_req,
                open_time=open_time,
                pos_id=pos_id,
            )
            self._ensure_trade_record(
                pos_id=pos_id,
                action=action,
                symbol=symbol,
                volume=volume,
                price=price,
                sl=sl_price,
                tp=tp_price,
                comment=comment,
                requested_entry_price=price,
                open_time=open_time,
            )
        else:
            logger.error(
                f"Failed to open {action.upper()} position {self.trade.ResultRetcodeDescription()}"
            )
        return bool(result)

    def close_position(  # noqa: C901
        self,
        selected_pos: dict,
        reason: Optional[str] = None,
    ) -> bool:
        """Close a position using the selected position dict."""
        symbol = selected_pos.get("symbol", "")
        pos_type = selected_pos.get("type")
        is_buy = pos_type == mt5.POSITION_TYPE_BUY or str(pos_type).lower() == "buy"
        action = "buy" if is_buy else "sell"

        tick = self._ticks_data.get(symbol)
        if tick is None:
            logger.error("Tick data missing for position close")
            return False

        bid = float(tick.bid or 0.0)
        ask = float(tick.ask or 0.0)
        close_price = bid if is_buy else ask

        symbol_info = self._symbols_data.get(symbol)
        digits = symbol_info.digits if symbol_info is not None else 5
        tol = 10 ** (-int(digits))

        deal_info = {
            "reason": reason or "Unknown",
        }
        if reason is None:
            if is_buy:
                if np.isclose(float(selected_pos.get("tp", 0.0)), bid, atol=tol):
                    deal_info["reason"] = "Take profit"
                elif np.isclose(float(selected_pos.get("sl", 0.0)), bid, atol=tol):
                    deal_info["reason"] = "Stop loss"
            else:
                if np.isclose(float(selected_pos.get("tp", 0.0)), ask, atol=tol):
                    deal_info["reason"] = "Take profit"
                elif np.isclose(float(selected_pos.get("sl", 0.0)), ask, atol=tol):
                    deal_info["reason"] = "Stop loss"

        if self.mt5_client:
            profit = self.mt5_client.order_calc_profit(
                0 if action == "buy" else 1,
                symbol,
                float(selected_pos.get("volume", 0.0)),
                float(selected_pos.get("price_open", 0.0)),
                close_price,
            )
        else:
            # Fallback profit calculation if no MT5 client
            # Simple (close - open) * volume * contract_size
            vol = float(selected_pos.get("volume", 0.0))
            open_p = float(selected_pos.get("price_open", 0.0))
            contract_size = 100000.0  # Default fallback
            if symbol_info:
                contract_size = getattr(symbol_info, "trade_contract_size", 100000.0)

            if action == "buy":
                profit = (close_price - open_p) * vol * contract_size
            else:
                profit = (open_p - close_price) * vol * contract_size
        symbol_info = self._symbols_data.get(symbol)
        pos_type = int(selected_pos.get("type") or 0)
        close_costs = None
        if symbol_info is not None and hasattr(self._simulator, "_calc_close_costs"):
            close_costs = self._simulator._calc_close_costs(
                symbol_info=symbol_info,
                pos_type=pos_type,
                volume=float(selected_pos.get("volume", 0.0)),
                open_time=int(selected_pos.get("time") or 0),
                close_time=int(self._current_sim_time().timestamp()),
            )
        if close_costs is None:
            commission = float(selected_pos.get("commission", 0.0) or 0.0)
            fee = float(selected_pos.get("fee", 0.0) or 0.0)
            swap = float(selected_pos.get("swap", 0.0) or 0.0)
        else:
            commission, fee, swap = close_costs

        selected_pos["direction"] = "closed"

        pos_id = int(selected_pos.get("id") or selected_pos.get("ticket") or 0)
        if not self.trade.PositionClose(ticket=pos_id):
            logger.error(f"Close failed: {self.trade.ResultRetcodeDescription()}")
            return False

        position_state = getattr(self, "_position_array_state", None)
        if position_state is not None:
            position_state.remove(int(pos_id))

        record = self._trade_records_open.get(pos_id)
        if record is None:
            self._ensure_trade_record(
                pos_id=pos_id,
                action=action,
                symbol=symbol,
                volume=float(selected_pos.get("volume", 0.0)),
                price=float(selected_pos.get("price_open", 0.0)),
                sl=float(selected_pos.get("sl", 0.0)),
                tp=float(selected_pos.get("tp", 0.0)),
                comment=selected_pos.get("comment", ""),
                requested_entry_price=float(selected_pos.get("price_open", 0.0)),
                open_time=selected_pos.get("time"),
            )
            record = self._trade_records_open.get(pos_id)

        if record is not None:
            close_dt = self._current_sim_time()
            record.close_time = close_dt
            record.close_price = float(close_price)
            record.requested_exit_price = float(
                selected_pos.get("tp", 0.0) or selected_pos.get("sl", 0.0) or 0.0
            )
            if reason == "Take profit":
                record.close_type = "TP"
                record.exit_reason = "RISK_EXIT"
            elif reason == "Stop loss":
                record.close_type = "SL"
                record.exit_reason = "RISK_EXIT"
            elif reason == "Time exit":
                record.close_type = "TIME_EXIT"
                record.exit_reason = "TIMEOUT"
            elif reason:
                record.close_type = "SIGNAL_EXIT"
                record.exit_reason = "STRATEGY_EXIT"
            else:
                record.close_type = "UNKNOWN"
                record.exit_reason = "UNKNOWN"

            record.profit_loss = float(profit + commission + fee + swap)
            pip_size = self._pip_size(symbol)
            if pip_size > 0:
                if action == "buy":
                    record.profit_loss_pips = (
                        close_price - record.open_price
                    ) / pip_size
                else:
                    record.profit_loss_pips = (
                        record.open_price - close_price
                    ) / pip_size
            record.commission = commission + fee
            record.swap = swap

            tracker = self._trade_trackers.get(pos_id, {})
            record.bars_in_trade = int(tracker.get("bars_in_trade", 0))
            record.time_in_trade = float(
                (close_dt - (record.open_time or close_dt)).total_seconds()
            )
            record.mae_usd = abs(float(tracker.get("mae_usd", 0.0)))
            record.mfe_usd = float(tracker.get("mfe_usd", 0.0))
            record.mae_pips = abs(float(tracker.get("mae_pips", 0.0)))
            record.mfe_pips = float(tracker.get("mfe_pips", 0.0))

            if record.initial_risk_usd > 0:
                record.r_multiple = record.profit_loss / record.initial_risk_usd

            self._completed_trades.append(record)
            self._trade_records_open.pop(pos_id, None)
            self._trade_trackers.pop(pos_id, None)

        self._positions_data.pop(pos_id, None)
        return True

    def close_all_positions(self, reason: str = "Time exit") -> None:
        """Close all open positions using the latest tick data.

        This method iterates through all open positions and closes them with
        the specified reason. Useful for cleanup at end of backtest or when
        strategy needs to exit all positions.

        Args:
            reason: Exit reason to record for all closed positions.
                   Default is "Time exit".
        """
        positions = self._simulator.positions_get() or []
        for position in positions:
            pos_data = (
                position._asdict() if hasattr(position, "_asdict") else dict(position)
            )
            self.close_position(pos_data, reason=reason)

    # Pending Orders
    def _place_pending_order(
        self,
        order_type: str,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float,
        tp: float,
        comment: str,
        expiry_date: Optional[datetime],
        expiration_mode: str,
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a pending order into the simulator orders container."""
        # Normalize order type + expiration inputs
        normalized_type = self._normalize_pending_type(order_type)
        enum_name = self._pending_type_enum_name(normalized_type)
        if not enum_name:
            logger.error(f"Invalid pending order type: {order_type}")
            return False
        order_type_value = getattr(mt5, enum_name, None) or getattr(
            mt5, f"ORDER_TYPE_{enum_name}", None
        )
        if order_type_value is None:
            logger.error(f"Unknown MT5 order type: {enum_name}")
            return False

        expiration_mode_norm = str(expiration_mode or "gtc").strip().lower()
        expiry_date = self._normalize_expiry_date(expiry_date)

        # Map expiration to MT5 constants (best-effort).
        if expiration_mode_norm == "gtc":
            type_time = getattr(mt5, "ORDER_TIME_GTC", 0)
        elif expiration_mode_norm in ("day", "day_end"):
            type_time = getattr(mt5, "ORDER_TIME_DAY", 0)
        else:
            type_time = getattr(mt5, "ORDER_TIME_SPECIFIED", 0)

        # Stop-limit orders require a stoplimit value. We default to open_price.
        stoplimit = float(open_price) if "stop limit" in normalized_type else 0.0

        return bool(
            self.trade.OrderOpen(
                symbol=symbol,
                order_type=int(order_type_value),
                volume=float(volume),
                price=float(open_price),
                sl=float(sl),
                tp=float(tp),
                stoplimit=float(stoplimit),
                type_time=type_time,
                expiration=expiry_date,
                comment=comment,
            )
        )

    def buy_limit(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a buy limit pending order."""
        return self._place_pending_order(
            "buy limit",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            validator=validator,
        )

    def sell_limit(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a sell limit pending order."""
        return self._place_pending_order(
            "sell limit",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            validator=validator,
        )

    def buy_stop(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a buy stop pending order."""
        return self._place_pending_order(
            "buy stop",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            validator=validator,
        )

    def sell_stop(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a sell stop pending order."""
        return self._place_pending_order(
            "sell stop",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            validator=validator,
        )

    def buy_stop_limit(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a buy stop limit pending order."""
        return self._place_pending_order(
            "buy stop limit",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            validator=validator,
        )

    def sell_stop_limit(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Place a sell stop limit pending order."""
        return self._place_pending_order(
            "sell stop limit",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            validator=validator,
        )

    # Order Management
    def order_delete(self, selected_order: dict) -> bool:
        """Delete a pending order from the simulator container."""
        ticket = int(selected_order.get("ticket") or 0)
        if ticket <= 0:
            logger.error("Invalid order ticket for delete")
            return False
        if not self.trade.OrderDelete(ticket):
            logger.error(f"Order {ticket} not found for delete")
            return False
        return True

    def order_modify(
        self,
        order: dict,
        new_open_price: float,
        new_sl: float,
        new_tp: float,
        new_expiry: Optional[datetime] = None,
        new_expiration_mode: Optional[str] = None,
        validator: Optional[TradeValidator] = None,
    ) -> bool:
        """Modify a pending order in the simulator container."""
        ticket = int(order.get("ticket") or 0)
        if ticket <= 0:
            logger.error("Invalid order ticket for modify")
            return False

        expiration_mode = (
            str(new_expiration_mode).strip().lower() if new_expiration_mode else "gtc"
        )
        new_expiry = self._normalize_expiry_date(new_expiry)

        if expiration_mode == "gtc":
            type_time = getattr(mt5, "ORDER_TIME_GTC", 0)
        elif expiration_mode in ("day", "day_end"):
            type_time = getattr(mt5, "ORDER_TIME_DAY", 0)
        else:
            type_time = getattr(mt5, "ORDER_TIME_SPECIFIED", 0)

        return bool(
            self.trade.OrderModify(
                ticket=ticket,
                price=float(new_open_price),
                sl=float(new_sl),
                tp=float(new_tp),
                type_time=type_time,
                expiration=new_expiry,
            )
        )

    def modify_position(
        self,
        selected_pos: dict,
        new_sl: Optional[float] = None,
        new_tp: Optional[float] = None,
    ) -> bool:
        """Modify a position's SL/TP in the simulator container."""
        pos_id = int(selected_pos.get("id") or selected_pos.get("ticket") or 0)
        if pos_id <= 0:
            logger.error("Invalid position id for modify_position")
            return False

        return bool(
            self.trade.PositionModify(
                ticket=pos_id,
                sl=float(new_sl) if new_sl is not None else 0.0,
                tp=float(new_tp) if new_tp is not None else 0.0,
            )
        )



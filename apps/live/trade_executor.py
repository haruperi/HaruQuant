"""Trade Executor.

Executes trades based on strategy signals with retry logic and error handling.
"""

import time
from typing import Dict, Optional, Tuple, Union

from apps.live.position_manager import PositionManager
from apps.logger import logger
from apps.trading import OrderTypeFilling, SymbolInfo, Trade, TradeRetcode


class TradeExecutor:
    """Execute trades based on signals."""

    def __init__(
        self,
        trade: Trade,
        symbol_info: SymbolInfo,
        position_manager: PositionManager,
        symbol: str,
        volume: float,
        filling_mode: Optional[OrderTypeFilling] = None,
        max_retries: int = 3,
    ):
        """Initialize trade executor.

        Args:
            trade: Trade instance
            symbol_info: SymbolInfo instance
            position_manager: PositionManager instance
            symbol: Trading symbol
            volume: Fixed lot size
            filling_mode: Order filling mode for this symbol (FOK, IOC, RETURN)
            max_retries: Maximum retry attempts for transient errors
        """
        self.trade = trade
        self.symbol_info = symbol_info
        self.position_manager = position_manager
        self.symbol = symbol
        self.volume = volume
        self.filling_mode = filling_mode
        self.max_retries = max_retries

        logger.info(
            f"TradeExecutor initialized (symbol={symbol}, volume={volume}, "
            f"filling_mode={filling_mode.name if filling_mode else 'None'}, "
            f"max_retries={max_retries})"
        )

    def execute_signal(self, signal: Dict) -> Tuple[bool, str]:
        """Execute trade based on signal.

        Args:
            signal: Signal dictionary from strategy

        Returns:
            Tuple of (success: bool, message: str)
        """
        signal_type = signal.get("signal")

        if signal_type in ["buy", "sell"]:
            return self._execute_entry(signal)
        elif signal_type in ["close buy", "close sell"]:
            return self._execute_exit(signal)
        else:
            message = f"Unknown signal type: {signal_type}"
            logger.error(message)
            return False, message

    def _execute_entry(self, signal: Dict) -> Tuple[bool, str]:
        """Execute entry order (buy or sell).

        Args:
            signal: Signal dictionary

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            order_params = self._prepare_order_params(signal)
            if not order_params:
                return False, f"Invalid entry signal: {signal.get('signal')}"

            return self._execute_order_with_retry(order_params)

        except Exception as e:
            message = f"Exception executing {signal.get('signal')} order: {e}"
            logger.error(message, exc_info=True)
            return False, message

    def _prepare_order_params(self, signal: Dict) -> Optional[Dict]:
        """Prepare order parameters from signal."""
        signal_type = signal.get("signal")
        signal_time = signal.get("time")

        if self.filling_mode:
            self.trade.set_type_filling(self.filling_mode)

        if signal_type == "buy":
            price = self.symbol_info.ask()
            order_type = "BUY"
        elif signal_type == "sell":
            price = self.symbol_info.bid()
            order_type = "SELL"
        else:
            return None

        # Format comment
        time_str = signal_time.strftime("%Y%m%d_%H%M") if signal_time else "0000"
        comment = f"TF_{time_str}"

        return {
            "signal_type": signal_type,
            "order_type": order_type,
            "price": price,
            "sl": signal.get("stop_loss", 0.0) or 0.0,
            "tp": signal.get("take_profit", 0.0) or 0.0,
            "comment": comment,
        }

    def _execute_order_with_retry(self, params: Dict) -> Tuple[bool, str]:
        """Execute order with retry logic for transient errors."""
        order_type = params["order_type"]
        price = params["price"]
        signal_type = params["signal_type"]

        logger.info(f"Executing {order_type} order: {self.volume} lots at {price:.5f}")

        for attempt in range(1, self.max_retries + 1):
            success = self._send_order(signal_type, params)

            if success:
                return self._handle_success(order_type)

            # Handle failure
            retcode = self.trade.result_retcode()
            retcode_desc = self.trade.result_retcode_description()

            if self._is_transient_error(retcode) and attempt < self.max_retries:
                logger.warning(
                    f"Transient error on attempt {attempt}/{self.max_retries}: "
                    f"{retcode_desc}"
                )
                time.sleep(0.5)
                # Refresh price
                params["price"] = (
                    self.symbol_info.ask()
                    if signal_type == "buy"
                    else self.symbol_info.bid()
                )
                continue
            else:
                return self._handle_failure(order_type, retcode_desc)

        # Max retries exhausted
        message = f"{order_type} order failed after {self.max_retries} attempts"
        logger.error(message)
        return False, message

    def _send_order(self, signal_type: str, params: Dict) -> bool:
        """Send specific buy/sell order."""
        if signal_type == "buy":
            return self.trade.buy(
                volume=self.volume,
                symbol=self.symbol,
                price=params["price"],
                sl=params["sl"],
                tp=params["tp"],
                comment=params["comment"],
            )
        else:
            return self.trade.sell(
                volume=self.volume,
                symbol=self.symbol,
                price=params["price"],
                sl=params["sl"],
                tp=params["tp"],
                comment=params["comment"],
            )

    def _handle_success(self, order_type: str) -> Tuple[bool, str]:
        """Handle successful trade execution."""
        message = (
            f"{order_type} order executed successfully | "
            f"Order: #{self.trade.result_order()} | "
            f"Deal: #{self.trade.result_deal()} | "
            f"Price: {self.trade.result_price():.5f} | "
            f"Volume: {self.trade.result_volume()}"
        )
        logger.info(message, extra={"TRADE": True})
        return True, message

    def _is_transient_error(self, retcode: Union[int, TradeRetcode]) -> bool:
        """Check if error is transient and can be retried."""
        transient_codes = {
            TradeRetcode.REQUOTE.value,
            TradeRetcode.PRICE_CHANGED.value,
            TradeRetcode.PRICE_OFF.value,
            TradeRetcode.TIMEOUT.value,
        }

        # Handle both int and Enum input
        value = retcode.value if isinstance(retcode, TradeRetcode) else retcode
        return value in transient_codes

    def _handle_failure(self, order_type: str, retcode_desc: str) -> Tuple[bool, str]:
        """Handle final trade failure."""
        comment = self.trade.result_comment()
        message = (
            f"{order_type} order failed | Retcode: {retcode_desc} | "
            f"Comment: {comment}"
        )
        logger.error(message, extra={"TRADE": True})
        return False, message

    def _execute_exit(self, signal: Dict) -> Tuple[bool, str]:
        """Execute exit order (close positions).

        Args:
            signal: Signal dictionary

        Returns:
            Tuple of (success: bool, message: str)
        """
        signal_type = signal.get("signal")

        try:
            if self.filling_mode:
                self.trade.set_type_filling(self.filling_mode)

            tickets = self.position_manager.get_positions_to_close(str(signal_type))

            if not tickets:
                message = f"No positions to close for signal '{signal_type}'"
                logger.info(message)
                return True, message

            logger.info(
                f"Closing {len(tickets)} position(s) for signal '{signal_type}'"
            )

            success_count, failed_tickets = self._close_tickets(tickets)

            if failed_tickets:
                message = (
                    f"Closed {success_count}/{len(tickets)} positions. "
                    f"Failed: {failed_tickets}"
                )
                logger.warning(message)
                return success_count > 0, message
            else:
                message = f"Successfully closed {success_count} position(s)"
                logger.info(message)
                return True, message

        except Exception as e:
            message = f"Exception executing exit signal: {e}"
            logger.error(message, exc_info=True)
            return False, message

    def _close_tickets(self, tickets: list) -> Tuple[int, list]:
        """Close list of position tickets."""
        success_count = 0
        failed_tickets = []

        for ticket in tickets:
            if self.trade.position_close(ticket=ticket):
                success_count += 1
                logger.info(
                    f"Position #{ticket} closed successfully", extra={"TRADE": True}
                )
            else:
                failed_tickets.append(ticket)
                retcode_desc = self.trade.result_retcode_description()
                logger.error(
                    f"Failed to close position #{ticket}: {retcode_desc}",
                    extra={"TRADE": True},
                )

        return success_count, failed_tickets

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TradeExecutor(symbol={self.symbol}, volume={self.volume})"

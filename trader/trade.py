import json

import MetaTrader5 as mt5
import controller
import pandas as pd
from datetime import datetime
import time
import controller as ctrl


class MT5Trade:
    """
    A Python class to handle trading operations with MetaTrader5.
    This is a reimplementation of the MQL5 CTrade class functionality.
    """

    def __init__(self):
        self.initialized = ctrl.g_mt5_initialized

    def is_connected(self):
        """
        Check if connected to MetaTrader5 terminal.

        Returns:
            bool: True if connected, False otherwise.
        """
        if not self.initialized:
            return False

        return mt5.terminal_info() is not None

    def shutdown(self):
        """
        Shutdown connection to MetaTrader5 terminal.

        Returns:
            bool: True if shutdown was successful.
        """
        result = mt5.shutdown()
        if result:
            ctrl.logger.info("MT5 connection shut down successfully")
            self.initialized = False
        else:
            ctrl.logger.error("Failed to shut down MT5 connection")

        return result

    def account_info(self):
        """
        Get account information.

        Returns:
            dict: Account information or None if failed.
        """
        if not self.is_connected():
            ctrl.logger.error("Cannot get account info: Not connected to MT5")
            return None

        try:
            account_info = mt5.account_info()
            if account_info is None:
                error = mt5.last_error()
                ctrl.logger.error(f"Failed to get account info. Error code: {error[0]}, Error description: {error[1]}")
                return None

            # Convert to dictionary for easier access
            return {
                'login': account_info.login,
                'trade_mode': account_info.trade_mode,
                'leverage': account_info.leverage,
                'limit_orders': account_info.limit_orders,
                'margin_so_mode': account_info.margin_so_mode,
                'trade_allowed': account_info.trade_allowed,
                'trade_expert': account_info.trade_expert,
                'balance': account_info.balance,
                'credit': account_info.credit,
                'profit': account_info.profit,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'margin_so_call': account_info.margin_so_call,
                'margin_so_so': account_info.margin_so_so,
                'currency': account_info.currency,
                'server': account_info.server,
                'company': account_info.company,
                'name': account_info.name
            }
        except Exception as e:
            ctrl.logger.error(f"Error getting account info: {str(e)}")
            return None

    def market_order(self, symbol, volume, buy=False, sell=False, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage, magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        """
        Place a Market BUY order on MetaTrader 5.

        Parameters:
        symbol (str): The symbol to trade (e.g., "EURUSD")
        volume (float): The volume of the trade in lots
        stop_loss (float, optional): Stop Loss price
        take_profit (float, optional): Take Profit price
        comment (str, optional): Comment for the order

        Returns:
        dict: Order result information
        """
        try:
            # Prepare the request structure
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            if sell:
                request["type"] = mt5.ORDER_TYPE_SELL
                if stop_loss_pips:
                    request["sl"] = mt5.symbol_info_tick(symbol).bid + stop_loss_pips * mt5.symbol_info(
                        symbol).point * 10
                if take_profit_pips:
                    request["tp"] = mt5.symbol_info_tick(symbol).ask - take_profit_pips * mt5.symbol_info(
                        symbol).point * 10

            if buy:
                request["type"] = mt5.ORDER_TYPE_BUY
                if stop_loss_pips:
                    request["sl"] = mt5.symbol_info_tick(symbol).ask - stop_loss_pips * mt5.symbol_info(symbol).point*10
                if take_profit_pips:
                    request["tp"] = mt5.symbol_info_tick(symbol).bid + take_profit_pips * mt5.symbol_info(symbol).point*10
            if comment:
                request["comment"] = comment
            if comment:
                request["comment"] = comment
            if magic_number:
                request["magic"] = magic_number
            if slippage:
                request["deviation"] = slippage

            # Send the order
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                message = {
                    "success": False,
                    "retcode": result.retcode,
                    "comment": result.comment
                }

                success_message = ctrl.compose_markdown_message(
                    title="Trading Alert!",
                    text="Order failed.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                ctrl.send_telegram_alert(message=success_message)
                return message

            else:
                message = {
                    "success": True,
                    "ticket_id": result.order,
                    "symbol": symbol,
                    "volume": result.volume,
                    "type": "Buy" if buy else "Sell",
                    "price": result.price,
                    "comment": result.comment
                }

                success_message = ctrl.compose_markdown_message(
                    title="Trading Alert!",
                    text="A new trade as been entered.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                ctrl.send_telegram_alert(message=success_message)
                return message

        except Exception as e:
            ctrl.logger.error(f"Error placing market BUY order: {str(e)}")
            return {"success": False, "message": str(e)}

    def pending_order(self, symbol, volume, order_type, price, stop_loss_pips=None, take_profit_pips=None,
                      slippage=None, magic_number=None, comment="HaruQuant"):
        """
        Place a Pending order on MetaTrader 5.

        Parameters:
        symbol (str): The symbol to trade (e.g., "EURUSD")
        volume (float): The volume of the trade in lots
        order_type (str): Type of pending order ('buy_limit', 'sell_limit', 'buy_stop', 'sell_stop')
        price (float): The price at which the pending order should be executed
        stop_loss_pips (float, optional): Stop Loss in pips
        take_profit_pips (float, optional): Take Profit in pips
        slippage (int, optional): Maximum price slippage for order execution
        magic_number (int, optional): Expert Advisor ID
        comment (str, optional): Comment for the order

        Returns:
        dict: Order result information
        """
        try:
            # Check connection
            if not self.is_connected():
                ctrl.logger.error("Cannot place pending order: Not connected to MT5")
                return {"success": False, "message": "Not connected to MT5"}

            # Get current market price for validation
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                ctrl.logger.error(f"Failed to get symbol info for {symbol}")
                return {"success": False, "message": f"Failed to get symbol info for {symbol}"}

            current_bid = tick.bid
            current_ask = tick.ask

            # Validate price based on order type
            if order_type == 'buy_limit' and price >= current_ask:
                ctrl.logger.warning(f"Buy Limit price ({price}) should be below current Ask price ({current_ask})")
            elif order_type == 'sell_limit' and price <= current_bid:
                ctrl.logger.warning(f"Sell Limit price ({price}) should be above current Bid price ({current_bid})")
            elif order_type == 'buy_stop' and price <= current_ask:
                ctrl.logger.warning(f"Buy Stop price ({price}) should be above current Ask price ({current_ask})")
            elif order_type == 'sell_stop' and price >= current_bid:
                ctrl.logger.warning(f"Sell Stop price ({price}) should be below current Bid price ({current_bid})")

            # Prepare the request structure
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "price": price,
                "type_filling": mt5.ORDER_FILLING_FOK,  # Changed from IOC to FOK
                "type_time": mt5.ORDER_TIME_GTC,
            }

            # Set the order type
            if order_type == 'buy_limit':
                request["type"] = mt5.ORDER_TYPE_BUY_LIMIT
            elif order_type == 'sell_limit':
                request["type"] = mt5.ORDER_TYPE_SELL_LIMIT
            elif order_type == 'buy_stop':
                request["type"] = mt5.ORDER_TYPE_BUY_STOP
            elif order_type == 'sell_stop':
                request["type"] = mt5.ORDER_TYPE_SELL_STOP
            else:
                raise ValueError("Invalid order type. Use 'buy_limit', 'sell_limit', 'buy_stop', or 'sell_stop'.")

            # Set Stop Loss and Take Profit
            point = mt5.symbol_info(symbol).point
            if stop_loss_pips:
                if order_type in ['buy_limit', 'buy_stop']:
                    request["sl"] = price - stop_loss_pips * point * 10
                else:
                    request["sl"] = price + stop_loss_pips * point * 10

            if take_profit_pips:
                if order_type in ['buy_limit', 'buy_stop']:
                    request["tp"] = price + take_profit_pips * point * 10
                else:
                    request["tp"] = price - take_profit_pips * point * 10

            if comment:
                request["comment"] = comment
            if magic_number:
                request["magic"] = magic_number
            if slippage:
                request["deviation"] = slippage

            # Log the request for debugging
            ctrl.logger.info(f"Sending pending order request: {request}")

            # Send the order
            result = mt5.order_send(request)

            # Log the raw result for debugging
            ctrl.logger.info(f"Order result: {result}")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_code = result.retcode
                error_desc = mt5.last_error()

                message = {
                    "success": False,
                    "retcode": error_code,
                    "description": str(error_desc),
                    "comment": result.comment
                }

                error_message = ctrl.compose_markdown_message(
                    title="Trading Alert!",
                    text=f"Pending order failed. Error code: {error_code}",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                ctrl.send_telegram_alert(message=error_message)
                ctrl.logger.error(f"Pending order failed: {message}")
                return message

            else:
                message = {
                    "success": True,
                    "ticket_id": result.order,
                    "volume": result.volume,
                    "type": order_type,
                    "price": price,
                    "comment": result.comment
                }

                success_message = ctrl.compose_markdown_message(
                    title="Trading Alert!",
                    text="A new pending order has been placed.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                ctrl.send_telegram_alert(message=success_message)
                return message

        except Exception as e:
            ctrl.logger.error(f"Error placing pending order: {str(e)}")
            import traceback
            ctrl.logger.error(traceback.format_exc())
            return {"success": False, "message": str(e)}

    def buy(self, symbol, volume, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage,
            magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        return self.market_order(symbol, volume, True, False, stop_loss_pips, take_profit_pips, slippage, magic_number,
                                 comment)

    def sell(self, symbol, volume, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage,
             magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        return self.market_order(symbol, volume, False, True, stop_loss_pips, take_profit_pips, slippage, magic_number,
                                 comment)

    def buy_limit(self, symbol, volume, price, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage,
                  magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        return self.pending_order(symbol, volume, 'buy_limit', price, stop_loss_pips, take_profit_pips, slippage,
                                  magic_number, comment)

    def sell_limit(self, symbol, volume, price, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage,
                   magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        return self.pending_order(symbol, volume, 'sell_limit', price, stop_loss_pips, take_profit_pips, slippage,
                                  magic_number, comment)

    def buy_stop(self, symbol, volume, price, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage,
                 magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        return self.pending_order(symbol, volume, 'buy_stop', price, stop_loss_pips, take_profit_pips, slippage,
                                  magic_number, comment)

    def sell_stop(self, symbol, volume, price, stop_loss_pips=None, take_profit_pips=None, slippage=ctrl.g_slippage,
                  magic_number=ctrl.g_magic_number, comment=ctrl.g_comment):
        return self.pending_order(symbol, volume, 'sell_stop', price, stop_loss_pips, take_profit_pips, slippage,
                                  magic_number, comment)

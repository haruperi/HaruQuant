import json
import MetaTrader5 as mt5
from logger import logger
from notification import *

class Trade:
    RetCodes = {10027: "Enable Algo Trading in MetaTrader5 app", 10018: "Market closed", 10016: "Wrong SL"}

    def __init__(self):
        # Initialize MetaTrader 5 connection if not already done
        if not mt5.initialize():
            logger.error("MetaTrader5 initialization failed")
            send_telegram_alert(message="MetaTrader5 initialization failed")
            raise Exception("MetaTrader5 initialization failed")

    def market_order(self, symbol, volume, buy=False, sell=False, stop_loss_pips=None, take_profit_pips=None, slippage=None, magic_number=None, comment="HaruQuant"):
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

                success_message = compose_markdown_message(
                    title="Trading Alert!",
                    text="Order failed.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                send_telegram_alert(message=success_message)
                return message

            else:
                message = {
                    "success": True,
                    "ticket_id": result.order,
                    "volume": result.volume,
                    "type": "Buy" if buy else "Sell",
                    "price": result.price,
                    "comment": result.comment
                }

                success_message = compose_markdown_message(
                    title="Trading Alert!",
                    text="A new trade as been entered.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                send_telegram_alert(message=success_message)
                return message

        except Exception as e:
            logger.error(f"Error placing market BUY order: {str(e)}")
            return {"success": False, "message": str(e)}


    def pending_order(self, symbol, volume, order_type, price, stop_loss_pips=None, take_profit_pips=None, slippage=None, magic_number=None, comment="HaruQuant"):
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
            # Prepare the request structure
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "price": price,
                "type_filling": mt5.ORDER_FILLING_IOC,
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
            if stop_loss_pips:
                if order_type in ['buy_limit', 'buy_stop']:
                    request["sl"] = price - stop_loss_pips * mt5.symbol_info(symbol).point * 10
                else:
                    request["sl"] = price + stop_loss_pips * mt5.symbol_info(symbol).point * 10

            if take_profit_pips:
                if order_type in ['buy_limit', 'buy_stop']:
                    request["tp"] = price + take_profit_pips * mt5.symbol_info(symbol).point * 10
                else:
                    request["tp"] = price - take_profit_pips * mt5.symbol_info(symbol).point * 10

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

                error_message = compose_markdown_message(
                    title="Trading Alert!",
                    text="Pending order failed.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                send_telegram_alert(message=error_message)
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

                print(result)

                success_message = compose_markdown_message(
                    title="Trading Alert!",
                    text="A new pending order has been placed.",
                    details={},
                    code_blocks={"json": f"{json.dumps(message, indent=4)}"},
                )
                send_telegram_alert(message=success_message)
                return message

        except Exception as e:
            logger.error(f"Error placing pending order: {str(e)}")
            return {"success": False, "message": str(e)}


# Example usage:
if __name__ == "__main__":
    trade = Trade()
    #trade.market_order("EURUSD", 0.1, buy=True, sell=False, stop_loss_pips=10, take_profit_pips=10, slippage=20, magic_number=1988)
    trade.pending_order("EURUSD", 0.1, "sell_limit", 1.050, stop_loss_pips=10, take_profit_pips=20,
                                 slippage=20, magic_number=1988)
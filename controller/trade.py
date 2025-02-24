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
                    details=message,
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

    # ... (other methods of the Trade class)

# Example usage:
if __name__ == "__main__":
    trade = Trade()
    trade.market_order("EURUSD", 0.1, buy=True, sell=False, stop_loss_pips=10, take_profit_pips=10, slippage=20, magic_number=1988)
import json
import MetaTrader5 as mt5
import pandas as pd

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

    def get_open_positions_and_orders(self):
        """
        Retrieve open positions and pending orders from MetaTrader 5.

        Returns:
        dict: A dictionary containing two pandas DataFrames:
              'positions' for open positions and 'orders' for pending orders.
        """
        try:
            # Fetch open positions
            positions = mt5.positions_get()
            if positions is None:
                logger.warning("No open positions")
                positions_df = pd.DataFrame()
            else:
                positions_df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
                logger.info(f"Retrieved {len(positions_df)} open positions")

            # Fetch pending orders
            orders = mt5.orders_get()
            if orders is None:
                logger.warning("Failed to get orders")
                orders_df = pd.DataFrame()
            else:
                orders_df = pd.DataFrame(list(orders), columns=orders[0]._asdict().keys())
                logger.info(f"Retrieved {len(orders_df)} pending orders")


            # Log the raw data
            logger.debug(f"Raw positions data: {positions_df.to_dict(orient='records')}")
            logger.debug(f"Raw orders data: {orders_df.to_dict(orient='records')}")

            # Process and clean the DataFrames
            for df, df_name in [(positions_df, 'positions'), (orders_df, 'orders')]:
                if not df.empty:
                    logger.info(f"Processing {df_name} DataFrame with initial shape: {df.shape}")

                    # Convert time columns to datetime
                    time_columns = ['time', 'time_setup', 'time_setup_msc', 'time_expiration', 'time_done',
                                    'time_done_msc']
                    for col in time_columns:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], unit='s', errors='coerce')
                            logger.debug(f"Converted {col} to datetime for {df_name}")

                    # Convert numeric columns to appropriate types
                    numeric_columns = ['volume', 'price_open', 'sl', 'tp', 'price_current', 'swap', 'profit']
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            logger.debug(f"Converted {col} to numeric for {df_name}")


            result = {
                'positions': positions_df,
                'orders': orders_df
            }

            # Log summary
            logger.info(f"Final count: {len(positions_df)} open positions and {len(orders_df)} pending orders")

            # Prepare and send Telegram notification
            message = {
                "open_positions": len(positions_df),
                "pending_orders": len(orders_df)
            }
            notification = compose_markdown_message(
                title="Account Status Update",
                text="Open positions and pending orders retrieved.",
                details={},
                code_blocks={"json": json.dumps(message, indent=4)}
            )
            send_telegram_alert(message=notification)

            return result

        except Exception as e:
            error_msg = f"Error retrieving open positions and pending orders: {str(e)}"
            logger.error(error_msg)
            send_telegram_alert(message=error_msg)
            return {"success": False, "message": error_msg}


    def close_all_positions(self):
        """
        Close all open positions.

        Returns:
        dict: A dictionary containing the results of the closing operations.
        """
        try:
            # Get all open positions
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                logger.info("No open positions to close.")
                return {"success": True, "message": "No open positions to close.", "closed_positions": 0}

            closed_positions = 0
            failed_closures = []

            for position in positions:
                # Prepare the request to close the position
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": position.symbol,
                    "volume": position.volume,
                    "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": position.ticket,
                    "price": mt5.symbol_info_tick(
                        position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(
                        position.symbol).ask,
                    "deviation": 20,
                    "magic": position.magic,
                    "comment": "Position closed by HaruQuant",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                # Send the order to close the position
                result = mt5.order_send(request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"Failed to close position {position.ticket}: {result.comment}")
                    failed_closures.append({"ticket": position.ticket, "reason": result.comment})
                else:
                    closed_positions += 1
                    logger.info(f"Successfully closed position {position.ticket}")

            # Prepare the result message
            result_message = {
                "success": True,
                "closed_positions": closed_positions,
                "failed_closures": failed_closures,
                "total_positions": len(positions)
            }

            # Log and send a Telegram notification
            log_message = f"Closed {closed_positions} out of {len(positions)} positions."
            if failed_closures:
                log_message += f" {len(failed_closures)} positions failed to close."
            logger.info(log_message)

            notification = compose_markdown_message(
                title="Position Closure Report",
                text=log_message,
                details={},
                code_blocks={"json": json.dumps(result_message, indent=4)}
            )
            send_telegram_alert(message=notification)

            return result_message

        except Exception as e:
            error_msg = f"Error while closing positions: {str(e)}"
            logger.error(error_msg)
            send_telegram_alert(message=error_msg)
            return {"success": False, "message": error_msg}


    def close_all_pending_orders(self):
        """
        Close all pending orders.

        Returns:
        dict: A dictionary containing the results of the closing operations.
        """
        try:
            # Get all pending orders
            orders = mt5.orders_get()
            if orders is None or len(orders) == 0:
                logger.info("No pending orders to close.")
                return {"success": True, "message": "No pending orders to close.", "closed_orders": 0}

            closed_orders = 0
            failed_closures = []

            for order in orders:
                # Prepare the request to delete the pending order
                request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                    "comment": "Order removed by script"
                }

                # Send the request to delete the pending order
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    closed_orders += 1
                    logger.info(f"Successfully closed pending order {order.ticket}")
                else:
                    error = f"Failed with error code: {result.retcode}"
                    logger.error(f"Failed to close pending order {order.ticket}: {error}")
                    failed_closures.append({"ticket": order.ticket, "reason": error})

            # Prepare the result message
            result_message = {
                "success": True,
                "closed_orders": closed_orders,
                "failed_closures": failed_closures,
                "total_orders": len(orders)
            }

            # Log and send a Telegram notification
            log_message = f"Closed {closed_orders} out of {len(orders)} pending orders."
            if failed_closures:
                log_message += f" {len(failed_closures)} orders failed to close."
            logger.info(log_message)

            notification = compose_markdown_message(
                title="Pending Order Closure Report",
                text=log_message,
                details={},
                code_blocks={"json": json.dumps(result_message, indent=4)}
            )
            send_telegram_alert(message=notification)

            return result_message

        except Exception as e:
            error_msg = f"Error while closing pending orders: {str(e)}"
            logger.error(error_msg)
            send_telegram_alert(message=error_msg)
            return {"success": False, "message": error_msg}


# TODO: Modify entry, SL, and TP for pending Limit Orders or cancel pending orders
#   - Add functionality to update order parameters or cancel pending orders based on conditions

# TODO: Modify SL and TP for open positions
#   - Implement functions to adjust stop loss (SL) and take profit (TP) for active positions

# TODO: Close any open positions
#   - Create routines to liquidate positions when needed


# TODO: Report whether open position modification, alerts, and notification results were successful to Telegram
#   - Confirm changes and send feedback through Telegram for monitoring

# TODO: Access the closed positions and deals from the OrderBook History and return the data table as a pandas DataFrame
#   - Retrieve historical data from the order book and process it into a DataFrame

# TODO: Print live floating equity and PnL
#   - Implement real-time monitoring of floating equity and profit & loss

# TODO: Generate time series data of the balance curve
#   - Store historical balance data and generate a time series representation for performance tracking
import time
from MetaTrader5 import *
import colorama
import pyautogui

colorama.init()


def get_position_size(symbol_info, stop_pips, max_risk_per_trade=5, risk_base_amount=300):
    """
    Calculate position size in lots based on account balance, risk percentage, stop loss in pips, and pip value.

    Parameters:
        stop_pips (float):  Stop loss distance in pips.
        max_risk_per_trade (float): Maximum risk percentage of the account balance for one trade.
        risk_base_amount (float): The base amount of capital to calculate the risk in dollars.
        symbol_info (dic): The value of one tick or point movement in the currency of the account.

    Returns:
        float: The calculated lot size, rounded to two decimal places.
    """
    pip_value_per_lot = 10 * symbol_info.trade_tick_value
    money_risk = risk_base_amount * (max_risk_per_trade / 100)              # Calculate the amount of money to risk
    pip_risk_value = stop_pips * pip_value_per_lot                          # Calculate the value per pip for the desired stop loss
    lot_size = (money_risk / pip_risk_value)                                # Calculate the position size in lots

    return max(0, round(lot_size, 2))                                       # Ensure position size is non-negative


# TODO: Place various kinds of orders
#   - Market BUY, Market SELL
#   - LIMIT BUY, LIMIT SELL
#   - STOP LIMIT BUY/SELL

# TODO: Evaluate the result of order placement and report if successful or not to Telegram
#   - Check order execution confirmation and send the appropriate notification

# TODO: Retrieve open positions and pending orders
#   - Develop functions to fetch open positions and pending orders from the system

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
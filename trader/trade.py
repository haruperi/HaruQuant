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
        self.magic_number = ctrl.g_magic_number
        self.deviation = ctrl.g_slippage

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
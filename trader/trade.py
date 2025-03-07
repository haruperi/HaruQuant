import MetaTrader5 as mt5
import controller
import pandas as pd
from datetime import datetime
import time
import logging


class MT5Trade:
    """
    A Python class to handle trading operations with MetaTrader5.
    This is a reimplementation of the MQL5 CTrade class functionality.
    """

    def __init__(self, path=None):
        """
        Initialize the MT5Trade class.

        Args:
            path (str, optional): Path to the MetaTrader5 terminal executable.
        """
        self.initialized = False
        self.magic_number = 0
        self.deviation = 10  # Default deviation in points
        self.logger = self._setup_logger()

        # Initialize connection to MetaTrader5
        self.initialized = self._initialize_mt5(path)

    def _setup_logger(self):
        """Set up logging for the MT5Trade class."""
        logger = logging.getLogger('MT5Trade')
        logger.setLevel(logging.INFO)

        # Create handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_mt5(self, path=None):
        """
        Initialize connection to MetaTrader5 terminal.

        Args:
            path (str, optional): Path to the MetaTrader5 terminal executable.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Shutdown MT5 if it was already initialized
            if mt5.terminal_info() is not None:
                mt5.shutdown()

            # Initialize MT5
            init_result = mt5.initialize(path=path)

            if not init_result:
                error = mt5.last_error()
                self.logger.error(f"MT5 initialization failed. Error code: {error[0]}, Error description: {error[1]}")
                return False

            # Check if connection is established
            if not mt5.terminal_info():
                self.logger.error("MT5 terminal info not available after initialization")
                return False

            self.logger.info("MT5 initialized successfully")
            self.logger.info(f"MT5 Terminal Info: {mt5.terminal_info()}")
            self.logger.info(f"MT5 Version: {mt5.version()}")

            return True
        except Exception as e:
            self.logger.error(f"Error initializing MT5: {str(e)}")
            return False

    def set_magic_number(self, magic):
        """
        Set the magic number (expert advisor ID) for trades.

        Args:
            magic (int): Magic number to identify trades.
        """
        self.magic_number = magic
        self.logger.info(f"Magic number set to {magic}")

    def set_deviation(self, deviation):
        """
        Set the maximum price deviation in points.

        Args:
            deviation (int): Maximum allowed deviation in points.
        """
        self.deviation = deviation
        self.logger.info(f"Deviation set to {deviation} points")

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
            self.logger.info("MT5 connection shut down successfully")
            self.initialized = False
        else:
            self.logger.error("Failed to shut down MT5 connection")

        return result

    def account_info(self):
        """
        Get account information.

        Returns:
            dict: Account information or None if failed.
        """
        if not self.is_connected():
            self.logger.error("Cannot get account info: Not connected to MT5")
            return None

        try:
            account_info = mt5.account_info()
            if account_info is None:
                error = mt5.last_error()
                self.logger.error(f"Failed to get account info. Error code: {error[0]}, Error description: {error[1]}")
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
            self.logger.error(f"Error getting account info: {str(e)}")
            return None
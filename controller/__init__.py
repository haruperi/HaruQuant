from .mylogger import *
import MetaTrader5 as mt5
from config.settings import *
from config.credentials import *

#----------------------------------------------------------------------------------------------#


#  Initialize connection to MetaTrader5 terminal.
if not g_mt5_initialized:
    try:
        mt5_init = mt5.initialize(
            login=mt5_login['username'],
            password=mt5_login['password'],
            server=mt5_login['server'],
            path=mt5_login['pathway']
        )

        if not mt5_init:
            err = mt5.last_error()
            logger.error(f"MT5 initialization failed. Error code: {err[0]}, Error description: {err[1]}")

        # Check if connection is established
        if not mt5.terminal_info():
            logger.error("MT5 terminal info not available after initialization")

        logger.info("MT5 initialized successfully")
        logger.info(f"MT5 Terminal Info: {mt5.terminal_info()}")
        logger.info(f"MT5 Version: {mt5.version()}")

        mt5_symbols = mt5.symbols_get()     # Get all symbols from MT5
        mt5_symbols_set = {symbol.name for symbol in mt5_symbols}   # Create a set of all MT5 symbols for quick lookup

        # Iterate through my_symbols to check if they exist in mt5_symbols
        for symbol in g_symbols_forex:
            if symbol in mt5_symbols_set:
                result = mt5.symbol_select(symbol, True)     # Attempt to initialize/enable the symbol
                if not result:
                    logger.error(f"Failed to enable {symbol}.")
            else:
                logger.error(f"{symbol} does not exist in MT5 symbols. Please update symbol name.")

        g_mt5_initialized = True

    except Exception as e:
        logger.error(f"Error initializing MT5: {str(e)}")

from .data import *
from .technicals import *
from .risk import *
from .strategy import *
from .notification import *
from .database import *
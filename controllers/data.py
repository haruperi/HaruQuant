##############################################################################################
##                            DATA EXTRACTION FILE                                          ##
##############################################################################################
import json
import os
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
import pickle


#----------------------------------------------------------------------------------------------#


def get_project_settings(import_filepath):
    """
    Reads credentials from a specified JSON file.

    Args:
        import_filepath (str): The file path to the settings.json file.

    Returns:
        dict: The project credentials as a dictionary.

    Raises:
        ImportError: If the file does not exist at the specified path.
    """
    # Test the filepath to make sure it exists
    if os.path.exists(import_filepath):
        # If yes, import the file
        f = open(import_filepath, "r")
        # Read the information
        settings = json.load(f)
        # Close the file
        f.close()
        # Return the project settings
        return settings
    # Notify user if settings.json doesn't exist
    else:
        raise ImportError("settings.json does not exist at provided location")


#----------------------------------------------------------------------------------------------#


def initialize_mt5(project_settings):
    """
    Initializes and logs in to the MetaTrader 5 (MT5) platform.

    This function utilizes the provided project settings to initialize 
    the MT5 terminal and log in using the credentials and server details.

    Args:
        project_settings (dict): A dictionary containing MT5 login information, including:
            - 'username' (str): The username for login.
            - 'password' (str): The password for the MT5 account.
            - 'server' (str): The server name used for the MT5 connection.
            - 'pathway' (str): The file path to the MT5 terminal executable.

    Returns:
        bool: True if MT5 is initialized and login is successful, False otherwise.
    """
    # Attempt to start MT5
    # Ensure that all variables are set to the correct type
    username = project_settings['mt5']['username']
    username = int(username)
    password = project_settings['mt5']['password']
    server = project_settings['mt5']['server']
    pathway = project_settings['mt5']['pathway']

    # Attempt to initialize MT5
    try:
        mt5_init = mt5.initialize(
            login=username,
            password=password,
            server=server,
            path=pathway
        )
    except Exception as e:
        print(f"Error initializing MetaTrader 5: {e}")
        # I cover more advanced error handling in other courses, which are useful for troubleshooting
        mt5_init = False

    # If MT5 initialized, attempt to log in to MT5
    mt5_login = False
    if mt5_init:
        try:
            mt5_login = mt5.login(
                login=username,
                password=password,
                server=server
            )
        except Exception as e:
            print(f"Error logging into MetaTrader 5: {e}")
            mt5_login = False

    # Return the outcome to the user
    if mt5_login:
        return True
    # Default fail condition of not logged in
    return False


#------------------------------------------------------------------------------------------------------#


def enable_all_symbols(symbols):
    """
    Enables all specified symbols in the MetaTrader 5 platform.

    Args:
        symbols (list): A list of symbol names to be enabled.

    Returns:
        bool: True if all symbols were successfully enabled, False otherwise.
    """

    # Get all symbols from MT5
    mt5_symbols = mt5.symbols_get()

    # Create a set of all MT5 symbols for quick lookup
    mt5_symbols_set = {symbol.name for symbol in mt5_symbols}

    # Iterate through my_symbols to check if they exist in mt5_symbols
    for symbol in symbols:
        if symbol in mt5_symbols_set:
            # Attempt to initialize/enable the symbol
            result = mt5.symbol_select(symbol, True)
            if not result:
                print(f"Failed to enable {symbol}.")
        else:
            print(f"{symbol} does not exist in MT5 symbols. Please update symbol name.")
            return False

    # Default to return True
    return True



#------------------------------------------------------------------------------------------------------#


def set_query_timeframe(timeframe):
    """
    Maps a given timeframe string to its corresponding MetaTrader 5 timeframe constant 
    and its duration in minutes.

    Args:
        timeframe (str): The string identifier for the timeframe (e.g., "M1", "H1", "D1").

    Returns:
        tuple: A tuple containing the MT5 constant for the timeframe and its duration in minutes.

    Raises:
        ValueError: If an invalid timeframe string is provided.
    """
    if timeframe == "M1":
        return mt5.TIMEFRAME_M1, 1
    elif timeframe == "M2":
        return mt5.TIMEFRAME_M2, 2
    elif timeframe == "M3":
        return mt5.TIMEFRAME_M3, 3
    elif timeframe == "M4":
        return mt5.TIMEFRAME_M4, 4
    elif timeframe == "M5":
        return mt5.TIMEFRAME_M5, 5
    elif timeframe == "M6":
        return mt5.TIMEFRAME_M6, 6
    elif timeframe == "M10":
        return mt5.TIMEFRAME_M10, 10
    elif timeframe == "M12":
        return mt5.TIMEFRAME_M12, 12
    elif timeframe == "M15":
        return mt5.TIMEFRAME_M15, 15
    elif timeframe == "M20":
        return mt5.TIMEFRAME_M20, 20
    elif timeframe == "M30":
        return mt5.TIMEFRAME_M30, 30
    elif timeframe == "H1":
        return mt5.TIMEFRAME_H1, 60
    elif timeframe == "H2":
        return mt5.TIMEFRAME_H2, 120
    elif timeframe == "H3":
        return mt5.TIMEFRAME_H3, 180
    elif timeframe == "H4":
        return mt5.TIMEFRAME_H4, 240
    elif timeframe == "H6":
        return mt5.TIMEFRAME_H6, 360
    elif timeframe == "H8":
        return mt5.TIMEFRAME_H8, 480
    elif timeframe == "H12":
        return mt5.TIMEFRAME_H12, 720
    elif timeframe == "D1":
        return mt5.TIMEFRAME_D1, 1440
    elif timeframe == "W1":
        return mt5.TIMEFRAME_W1, 10080
    elif timeframe == "MN1":
        return mt5.TIMEFRAME_MN1, 43200
    else:
        print(f"Incorrect timeframe provided. {timeframe}")
        raise ValueError



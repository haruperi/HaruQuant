##############################################################################################
##                            DATA EXTRACTION FILE                                          ##
##############################################################################################
import json
import os
import MetaTrader5 as mt5


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



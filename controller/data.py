##############################################################################################
##                            DATA EXTRACTION FILE                                          ##
##############################################################################################

import MetaTrader5 as mt5
import requests
from datetime import datetime
import pandas as pd
import pickle


#----------------------------------------------------------------------------------------------#

# TODO: Sentiment Data Order OrderBook
#   - Stock Twits Placement Access
#   - Social Media Feeds




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



#----------------------------------------------------------------------------------------------------------#


def fetch_data(symbol, timeframe, start_date=None, end_date=None, start_pos=None, end_pos=None, amibroker=False):
    """
    Fetches historical market data for the given symbol and timeframe.

    This function uses the MetaTrader 5 API to fetch candlestick data for a financial instrument
    (symbol) in a specified timeframe. The data can be retrieved either by date range or
    by positional indices.

    Args:
        symbol (str): The name of the financial instrument (e.g., "EURUSD").
        timeframe (str): The timeframe for the data (e.g., "M1", "H1").
        start_date (str, optional): The start date for the data in 'YYYY-MM-DD' format (default: None).
        end_date (str, optional): The end date for the data in 'YYYY-MM-DD' format (default: None).
        start_pos (int, optional): The positional index to start fetching data from (default: None).
        end_pos (int, optional): The positional index to stop fetching data at (default: None).

    Returns:
        pandas.DataFrame: A DataFrame containing historical data with the following columns:
            - Open
            - High
            - Low
            - Close

    Raises:
        ValueError: If no data is fetched for the specified symbol and time range.
        KeyError: If the 'time' field is not present in the fetched data.

    Note:
        Either 'start_date' and 'end_date' or 'start_pos' and 'end_pos' must be provided
        to fetch the data.
        :param end_pos:
        :param start_pos:
        :param end_date:
        :param start_date:
        :param timeframe:
        :param symbol:
        :param amibroker:

    """

    # Convert the timeframe into MT5 friendly format
    mt5_timeframe, time_delta = set_query_timeframe(timeframe=timeframe)

    # Convert dates to datetime objects
    start = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

    # Get Candles
    if start and end:
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start, end)
    else:
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, start_pos, end_pos)

    # Verify that rates contain data
    if rates is None or len(rates) == 0:
        raise ValueError(f"No data fetched for symbol {symbol} within the specified range.")

    # Convert to a dataframe
    dataframe = pd.DataFrame(rates)

    # Verify that the expected 'time' field is in the dataframe
    if 'time' not in dataframe:
        raise KeyError("'time' column is missing in the fetched data.")

    # Convert Datetime to be human-readable
    dataframe['DateTime'] = pd.to_datetime(dataframe['time'], unit='s')
    # Set Index of the dataframe
    dataframe.set_index('DateTime', inplace=True)

    if amibroker:
        # Split the DateTime into separate Date and Time columns
        dataframe['date'] = dataframe.index.date
        dataframe['time'] = dataframe.index.time
        dataframe = dataframe[["date", "time", "open", "high", "low", "close", "tick_volume"]]   # Use only wanted columns
        dataframe.columns = ["Date", "Time", "Open", "High", "Low", "Close", "Volume"]          # Rename columns for AmiBroker
        dataframe.to_csv(f'{symbol}.csv', index=False)  # Export the dataframe to a CSV file

    else:
        dataframe = dataframe[["open", "high", "low", "close"]]   # Use only wanted columns
        dataframe.columns = ["Open", "High", "Low", "Close"]      # Rename columns for MetaTrader 5

    return dataframe


#-----------------------------------------------------------------------------------------------------------#


def merge_symbols(symbols, trading_timeframe, start_date, end_date):
    """
    Merges historical market data for multiple symbols into a single DataFrame.

    This function fetches historical candlestick data for a list of financial instruments
    (symbols) in the specified timeframe. The data for each symbol is merged based on the
    datetime index, with the symbol's 'Close' values used as columns in the result.

    Args:
        symbols (list): A list of symbol names to fetch and merge (e.g., ["EURUSD", "GBPUSD"]).
        trading_timeframe (str): The timeframe for the data (e.g., "M5", "H1").
        start_date (str): The start date for the data in 'YYYY-MM-DD' format.
        end_date (str): The end date for the data in 'YYYY-MM-DD' format.

    Returns:
        pandas.DataFrame: A merged DataFrame where each column represents the 'Close' prices
        for the corresponding symbol. The index is the shared datetime.

    Raises:
        ValueError: If a symbol's data lacks the 'Close' column or cannot be fetched.

    Note:
        The merged DataFrame is exported as a CSV file named 'merged_data.csv'.

    Example:
        >>> merge_symbols(["EURUSD", "GBPUSD"], "M5", "2024-06-01", "2024-07-31")
    """
    data = pd.DataFrame()

    for symbol in symbols:
        df = fetch_data(symbol, trading_timeframe, start_date, end_date)

        # Ensure the DataFrame has a "close" column and a datetime index
        if "Close" not in df.columns:
            raise ValueError(f"DataFrame for {symbol} does not have a 'Close' column.")

        if data.empty:
            # Initialize the merged DataFrame with the first symbol's data
            data = df[["Close"]].rename(columns={"Close": symbol})
        else:
            # Merge on the index, renaming "close" to the symbol name
            data = data.join(df[["Close"]].rename(columns={"Close": symbol}), how="outer")

    data.to_csv("merged_data.csv")

    return data



#------------------------------------------------------------------------------------------------------#


def save_dictionary_to_file(data, filename):
    with open(filename, 'wb') as file:
        pickle.dump(data, file)

def load_dictionary_from_file(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)


def merge_full_symbols_data(symbols, trading_timeframe, start_date, end_date):
    """
    Merges historical market data for multiple symbols into unified aligned DataFrames.

    This function fetches candlestick data for a list of symbols within the specified timeframe
    and start/end dates, aligns their data to a unified index, and back-fills missing values.

    Args:
        symbols (list): A list of symbol names to fetch and merge (e.g., ["EURUSD", "GBPUSD"]).
        trading_timeframe (str): The timeframe for the data (e.g., "M5", "H1").
        start_date (str): The start date for fetching data ('YYYY-MM-DD' format).
        end_date (str): The end date for fetching data ('YYYY-MM-DD' format).

    Returns:
        dict: A dictionary with symbols as keys and their aligned DataFrames as values,
              saved to "merged_full_data.pkl" as a pickle file.
    """
    symbols_data = {}

    for symbol in symbols:  # Fetch raw data for all symbols
        symbols_data[symbol] = fetch_data(symbol, trading_timeframe, start_date, end_date)

    # Create a union of all indices
    all_indices = pd.concat([df.index.to_series() for df in symbols_data.values()]).drop_duplicates().sort_values()

    # Reindex all dataframes to the combined index and back-fill missing data
    aligned_data = {}
    for symbol, df in symbols_data.items():
        df = df.reindex(all_indices)  # Align to the union index
        df = df.bfill()  # Back-fill missing values
        aligned_data[symbol] = df

    save_dictionary_to_file(aligned_data, "merged_full_data.pkl")

    return aligned_data




def fetch_fundamental_data(api_key):
    url: str = "https://www.jblanked.com/news/api/forex-factory/calendar/today/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
        # for news in data:
        #    print(f"{news['Date']} {news['Currency']} {news['Name']} STRENGTH : {news['Strength']} OUTCOME : {news['Outcome']} ACTUAL : {news['Actual']} FORECAST : {news['Forecast']} PREVIOUS : {news['Previous']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None


########################################################################################################################
#                                         Technical Indicators functions
########################################################################################################################
from config.settings import *
import ta
from telegram import Bot




########################################################################################################################
#                                         Basic Indicators functions
########################################################################################################################




def calculate_moving_average(df, ma_type=g_ma_type, col=g_df_col, period=g_slow_ma):
    """
    Calculate the selected moving average (Simple, Exponential, or Weighted Moving Average)
    for a specified column in the DataFrame.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing price data.
        ma_type (str): Type of moving average to calculate.
                       Options are: 'sma' (Simple Moving Average),
                                    'ema' (Exponential Moving Average),
                                    'wma' (Weighted Moving Average).
        col (str): Name of the column for which the moving average will be calculated.
        period (int): The period (window size) for the moving average.

    Returns:
        pd.DataFrame: The DataFrame with an additional column containing the calculated moving average.
                      The column name will include the type and period of the moving average.
    """
    if ma_type == 'sma':
        df[f"SMA_{period}"] = ta.trend.SMAIndicator(df[col], int(period)).sma_indicator()
    if ma_type == 'ema':
        df[f"EMA_{period}"] = ta.trend.EMAIndicator(df[col], int(period)).ema_indicator()
    if ma_type == 'wma':
        df[f"WMA_{period}"] = ta.trend.WMAIndicator(df[col], int(period)).wma()

    return df





def calculate_rsi(df, col=g_df_col, period=g_rsi_period):
    """
    Calculate the Relative Strength Index (RSI) for a given column in the DataFrame.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing price data.
        col (str): Name of the column for which the RSI will be calculated.
        period (int): The period (window size) for the RSI calculation.

    Returns:
        pd.DataFrame: The DataFrame with an additional column containing the calculated RSI.
                      The column name will be 'RSI'.
    """
    df[f"RSI"] = ta.momentum.RSIIndicator(df[col], int(period)).rsi()

    return df





def calculate_williams_percent(df, period=g_willpct_period):
    """
    Calculate the Williams %R indicator for the given DataFrame.

    The Williams %R indicator measures the level of the current close price
    relative to the highest high and lowest low within a specified period.
    It is a momentum indicator that oscillates between -100 and 0.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing 'high', 'low', and 'close' columns.
        period (int): The time period to calculate Williams %R (e.g., 14).

    Returns:
        pd.DataFrame: The DataFrame with an additional column 'WPR' containing the Williams %R values.
    """
    df["WPR"] = ta.momentum.williams_r(df.High, df.Low, df.Close, int(period))

    return df





def calculate_atr(df, period=g_adr_period):
    """
    Calculate the Average True Range (ATR) indicator for a given DataFrame.

    ATR is a measure of market volatility, considering the entire range of an asset's price movements (highs, lows, closes)
    over a specified period.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing 'high', 'low', and 'close' columns.
        period (int): The time period for calculating the Average True Range.

    Returns:
        pd.DataFrame: The input DataFrame with an additional column 'ATR' that contains the calculated values.
    """
    df['ATR'] = ta.volatility.AverageTrueRange(df.High, df.Low, df.Close, window=period,fillna=False).average_true_range()

    return df




########################################################################################################################
#                                         Basic functions derived from basic indicators
########################################################################################################################




def get_adr(df, symbol_info, period=g_adr_period):
    """
    Calculate the Average Daily Range (ADR) and the current daily range percentage.

    Parameters:
    df (pd.DataFrame): DataFrame containing columns ['High', 'Low', 'Close'].
    period (int): The number of days over which to calculate the ADR.

    Returns:
    tuple: current ADR and current daily range percentage
    """
    # Calculate daily ranges
    df['daily_range'] = (df['High'] - df['Low']) / symbol_info.trade_tick_size

    # Calculate ADR
    df['ADR'] = df['daily_range'].rolling(window=period).mean()

    # Shift the ADR by one period to make today's ADR based on the previous value
    df['ADR'] = df['ADR'].shift(1)

    # Calculate the current daily range percentage
    current_daily_range = df['daily_range'].iloc[-1]
    current_adr = round(df['ADR'].iloc[-1])
    current_daily_range_percentage = round((current_daily_range / current_adr) * 100)

    return current_adr, current_daily_range_percentage





def get_position_size(tick_value, stop_points, MaxRiskPerTrade=g_max_risk_per_trade, RiskBaseAmount=g_risk_base_amount):
    """
    Calculate the optimal position size (lot size) for a trade based on risk parameters.

    Parameters:
        stop_points (float): Number of points from the entry to the stop-loss level.
        MaxRiskPerTrade (float): Maximum risk percentage of the account balance for one trade.
        RiskBaseAmount (float): The base amount of capital to calculate the risk in dollars.
        tick_value (float): The value of one tick or point movement in the currency of the account.

    Returns:
        float: The calculated lot size, rounded to two decimal places.
    """
    money_risk = RiskBaseAmount * (MaxRiskPerTrade / 100)
    lot_size = (money_risk / (stop_points * tick_value))

    return round(lot_size, 2)


def resample_to_timeframe(df, timeframe):
    """
    Resample lower timeframe data into a specified higher timeframe.

    Parameters:
    df (pd.DataFrame): Lower timeframe DataFrame with index as datetime and columns ['high', 'low', 'close', 'open'].
    symbol_info: Object containing symbol-specific info (e.g., trade_tick_size).
    timeframe (str): The target timeframe for resampling (e.g., 'D' for daily, 'W' for weekly).

    Returns:
    pd.DataFrame: Resampled DataFrame with columns ['Open', 'High', 'Low', 'Close'].
    """
    # Ensure the index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("The DataFrame index must be a DatetimeIndex.")

    # Resample to the specified timeframe
    resampled_data = df.resample(timeframe).agg({
        'Open': 'first',  # Opening price in the timeframe
        'High': 'max',  # Maximum price in the timeframe
        'Low': 'min',  # Minimum price in the timeframe
        'Close': 'last'  # Closing price in the timeframe
    })

    resampled_data.dropna(inplace=True)

    return resampled_data





async def send_telegram_message(token=g_token, chat_id=g_chat_id, message="Hello World"):
    """
    Send a message to a Telegram chat.

    Parameters:
    token (str): The bot token provided by the BotFather.
    chat_id (str): The chat ID or the username of the recipient.
    message (str): The message to send.
    """
    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=message)





def get_server_time(timeshift=0):
    """
    Get the current server time of the trading platform, adjusted for a specified time shift.

    This function retrieves the server time by accessing the latest tick data
    for a default symbol like 'EURUSD'. If the tick data is unavailable, it
    returns None. A time shift in hours can be applied to calculate
    a different time zone.

    Parameters:
        timeshift (int): The number of hours to adjust the server time. Defaults to 0.

    Returns:
        datetime: The adjusted server time, or None if the tick data is unavailable.
    """
    # Use a symbol that is always available to get the tick data
    tick = mt5.symbol_info_tick(g_test_symbol)
    if tick is None:
        print("Failed to get tick data")
        return None
    server_time = datetime.fromtimestamp(tick.time)

    # Apply the time shift
    adjusted_time = server_time + timedelta(hours=timeshift)

    return adjusted_time





def get_next_bar_time(server_time, interval_mins=5):
    """
    Calculate the next bar's timestamp based on the provided server time and time interval.

    This function adjusts the server time to the next valid bar opening time by rounding
    it up to the nearest interval. It ensures the calculated time aligns with the interval period.

    Parameters:
        server_time (datetime): The current server time to base the calculation on.
        interval_mins (int): The time interval in minutes (default is 5).

    Returns:
        datetime: The timestamp representing the next valid bar's start time.
    """
    next_bar_time = server_time.replace(second=0, microsecond=0) + timedelta(minutes=interval_mins)
    next_bar_time = next_bar_time - timedelta(minutes=server_time.minute % interval_mins)

    return next_bar_time
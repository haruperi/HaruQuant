########################################################################################################################
#                                         Technical Indicators functions
########################################################################################################################
from config.settings import *
import ta




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
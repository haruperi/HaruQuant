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






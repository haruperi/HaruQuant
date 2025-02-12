import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .technicals import *



def random(symbol):
    """
    Generates a random buy or sell signal.

    Args:
        symbol: The symbol (string) for which the signal is being generated.

    str: A string indicating the generated signal: "<symbol> Buy", "<symbol> Sell", or "<symbol> Neutral".
    """
    values = [-1, 0, 1]
    signal = np.random.choice(values)

    if signal == 1:
        return f"{symbol} Buy"
    elif signal == -1:
        return f"{symbol} Sell"
    else:
        return f"{symbol} Neutral"



def ma_trend_willpct_strategy(symbol, df, fast_sma_period=g_fast_ma,
                              slow_sma_period=g_slow_ma, williamsR_period=g_willpct_period):
    """
    Implements a trading strategy based on moving average trends and Williams %R oscillator.
    Filters the DataFrame to include only rows where the "isPivot" column is not NaN.

    Args:
        symbol (str): The trading symbol to analyze.
        :param df:
        :param williamsR_period:
        :param slow_sma_period:
        :param symbol:
        :param fast_sma_period:

    Returns:
        str: A string indicating the generated signal: "<symbol> Buy", "<symbol> Sell", or "<symbol> Neutral".
    """
    df = calculate_ma_trend_momentum_signals(df, fast_sma_period, slow_sma_period, williamsR_period)

    # Get current signal and time
    signal = df["signal"].iloc[-1]
    curr_time = df.index[-1]

    if signal == 1:
        return f"{curr_time} {symbol} Buy"
    elif signal == -1:
        return f"{curr_time} {symbol} Sell"
    else:
        return f"{curr_time} {symbol} Neutral"




def market_structure_strategy(symbol, ltf_df, htf_df):
    df = calculate_ltf_close_above_below_hft(ltf_df, htf_df)
    df = calculate_swingline_alerts(df)

    df = calculate_fractal_pivot_points(df)
    df = calculate_market_structure_signals(df)

    # Get current signal and time
    signal = df["signal"].iloc[-1]
    curr_time = df.index[-1]

    if signal == 1:
        return f"{curr_time} {symbol} Buy"
    elif signal == -1:
        return f"{curr_time} {symbol} Sell"
    else:
        return f"{curr_time} {symbol} Neutral"


def williams_percent_momentum_strategy(symbol, df):
    df = calculate_willpct_swing_lines(df)
    df = calculate_swingline_alerts(df)

    # Get current signal and time
    signal = df["signal"].iloc[-1]
    curr_time = df.index[-1]

    if signal == 0:
        return f"{curr_time} {symbol} Neutral"
    

    # df = calculate_fractal_pivot_points(df)
    # df = df[df["isPivot"].notna()]  # Filter rows where "isPivot" column is not NaN
    #
    # highs = df[df['isPivot'] == 1].High.tail(2).values
    # lows = df[df['isPivot'] == -1].Low.tail(2).values
    #
    # valid = highs[1] < highs[0] and lows[1] > lows[0]
    #
    # # return df
    #
    # if signal == 1 and valid:
    #     return f"{curr_time} {symbol} Buy"
    # elif signal == -1 and valid:
    #     return f"{curr_time} {symbol} Sell"
    # else:
    #     return f"{curr_time} {symbol} Neutral"

    if signal == 1:
        return f"{symbol} Buy"
    elif signal == -1:
        return f"{symbol} Sell"
    else:
        return f"{symbol} Neutral"

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
    signal_text = "Neutral"
    curr_time = df.index[-1]


    # By default, all positions are 0
    df["position"] = 0

    # If there's no signal, simply return with position zero
    if signal == 0:
        df.loc[curr_time, "position"] = 0
        return curr_time, f"{symbol} {signal_text}"

    # Calculate fractal pivot points using a copy of the DataFrame
    df = calculate_fractal_pivot_points(df.copy())
    df_fractal = df[df["isPivot"].notna()]

    # Get the last two pivot highs and lows
    highs = df_fractal[df_fractal['isPivot'] == 1].High.tail(2).values
    lows = df_fractal[df_fractal['isPivot'] == -1].Low.tail(2).values

    valid_buy = False
    valid_sell = False

    # Ensure we have enough data to compute valid_buy and valid_sell
    if len(highs) > 1 and len(lows) > 1:
        symbol_info = mt5.symbol_info(symbol)
        df = calculate_atr(df)
        atr = df.iloc[-1]["ATR"]
        buy_condition1 = (highs[1] < highs[0] ) and (lows[1] > lows[0] or atr >= abs(lows[1] - lows[0]))
        sell_condition1 = (lows[1] > lows[0] ) and (highs[1] < highs[0] or atr >= abs(highs[1] - highs[0]))

        valid_buy = buy_condition1
        valid_sell = sell_condition1


    # Determine the position based on signal and validation rules
    if signal == 1 and valid_buy:
        position = 1
        signal_text = "Buy"
    elif signal == -1 and valid_sell:
        position = -1
        signal_text = "Sell"
    else:
        position = 0

    # Update the "position" column for the last row only
    df.loc[curr_time, "position"] = position

    return curr_time, f"{symbol} {signal_text}"




def double_bottom_top_strategy(symbol, df):
    df = calculate_breakout_candles_swing_lines(df)
    df = calculate_fractal_pivot_points(df)
    df = calculate_doubles_signals(df)

    # Get current signal and time
    curr_time = df.index[-1]
    signal = df["signal"].iloc[-1]

    if signal == 1:
        return curr_time, f"{symbol} Buy"
    elif signal == -1:
        return curr_time, f"{symbol} Sell"
    else:
        return curr_time, f"{symbol} Neutral"

    #return df




###############################################################################################################
def williams_percent_momentum_strategy_backtest(symbol, df):
    # First, calculate the swing lines and alerts for the entire dataset.
    df = calculate_willpct_swing_lines(df)
    df = calculate_swingline_alerts(df)

    # Set up a position column with a default value of 0.
    # df["position"] = 0
    #
    # # Calculate fractal pivot points and ATR on the full dataframe.
    # # (Note: these functions are assumed to fill columns like "isPivot", "High", "Low", and "ATR")
    # df = calculate_fractal_pivot_points(df.copy())
    # df = calculate_atr(df)
    #
    # # Loop over the DataFrame row by row (assumed chronological order)
    # for i in range(len(df)):
    #     curr_time = df.index[i]
    #     signal = df["signal"].iloc[i]
    #
    #     # If no trading signal, keep position zero.
    #     if signal == 0:
    #         df.at[curr_time, "position"] = 0
    #         continue
    #
    #     # Use only data up to the current row to mimic real-time decision making.
    #     df_subset = df.iloc[:i + 1]
    #     df_fractal = df_subset[df_subset["isPivot"].notna()]
    #
    #     # Only attempt to calculate pivot conditions if we have at least two pivot highs and lows.
    #     pivot_highs = df_fractal[df_fractal['isPivot'] == 1]
    #     pivot_lows = df_fractal[df_fractal['isPivot'] == -1]
    #
    #     if len(pivot_highs) > 1 and len(pivot_lows) > 1:
    #         highs = pivot_highs.High.tail(2).values
    #         lows = pivot_lows.Low.tail(2).values
    #         atr = df_subset.iloc[-1]["ATR"]
    #
    #         # Define the conditions for a valid buy or sell.
    #         valid_buy = (highs[1] < highs[0]) and ((lows[1] > lows[0]) or (atr >= abs(lows[1] - lows[0])))
    #         valid_sell = (lows[1] > lows[0]) and ((highs[1] < highs[0]) or (atr >= abs(highs[1] - highs[0])))
    #
    #         # Determine the position based on signal and the validation conditions.
    #         if signal == 1 and valid_buy:
    #             pos = 1
    #         elif signal == -1 and valid_sell:
    #             pos = -1
    #         else:
    #             pos = 0
    #     else:
    #         pos = 0
    #
    #     df.at[curr_time, "position"] = pos

    return df
########################################################################################################################
#                                         Technical Indicators functions
########################################################################################################################
from config.settings import *
import ta
from telegram import Bot
import time
import numpy as np




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
    if ma_type == 'SMA':
        df[f"SMA_{period}"] = ta.trend.SMAIndicator(df[col], int(period)).sma_indicator()
    if ma_type == 'EMA':
        df[f"EMA_{period}"] = ta.trend.EMAIndicator(df[col], int(period)).ema_indicator()
    if ma_type == 'WMA':
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
    df["RSI"] = ta.momentum.RSIIndicator(df[col], int(period)).rsi()

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





def get_server_time(timeshift=g_time_shift):
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





def get_next_bar_time(server_time, interval_mins=g_interval_minutes):
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





def countdown_to_next_bar(interval_min=g_interval_minutes, timeShift=g_time_shift):
    """
    Continuously counts down to the opening of the next bar based on the server time and interval.

    This function retrieves the trading server time, determines the next bar time,
    and continuously sleeps until the new bar time is reached, at which point a task
    (e.g., live_run) can be executed.

    Parameters:
        interval_min (int): The time interval in minutes for the next bar's start. Default is 5.
        timeShift (int): The number of hours to adjust the server time. Default is 0.
    """

    server_time = get_server_time(timeShift)
    if server_time is None:
        return "Failed to get server time. Exiting..."

    next_bar_time = get_next_bar_time(server_time, interval_min)
    print(f"Next bar in: {next_bar_time}")

    while get_server_time(timeShift) < next_bar_time:
        time.sleep(1)

    # Perform the task at the opening of the new bar
    return f"\nNew bar opened at {next_bar_time}. Running the task..."





def calculate_currency_strength(symbols=g_symbols_forex, timeframe=g_trading_timeframe, strength_lookback=g_strength_lookback_period, strength_rsi=g_rsi_period, strength_loc=g_strength_loc):
    """
    Calculate currency strength based on RSI values for a set of currency pairs.

    The function fetches historical data for each currency pair, computes the RSI for
    a specified lookback period, and aggregates these values to calculate the relative
    strength of major currencies (USD, EUR, GBP, CHF, JPY, AUD, CAD, NZD).

    Parameters:
        symbols (list of str): List of currency pairs (e.g., ['EURUSD', 'GBPUSD']).
        timeframe (str): Timeframe for fetching data (e.g., 'H1', 'D1').
        strength_lookback (int): Number of past periods to include in calculating RSI.
        strength_rsi (int): RSI period for calculation.
        strength_loc (int): Position index to fetch the latest strength readings.

    Returns:
        pd.Series: A series of currency strength values (sorted in descending order).
    """
    data = pd.DataFrame()
    for symbol in symbols:
        df = fetch_data(symbol, timeframe, start_pos=0, end_pos=strength_lookback)
        df = calculate_rsi(df, g_df_col, strength_rsi)
        data[symbol] = df['RSI']

    strength = pd.DataFrame()
    strength["USD"] = 1 / 7 * (
                (100 - data.EURUSD) + (100 - data.GBPUSD) + data.USDCAD + data.USDJPY + (100 - data.NZDUSD) + (
                    100 - data.AUDUSD) + data.USDCHF)
    strength["EUR"] = 1 / 7 * (data.EURUSD + data.EURGBP + data.EURAUD + data.EURNZD + data.EURCHF + data.EURCAD)
    strength["GBP"] = 1 / 7 * (
                data.GBPUSD + data.GBPJPY + data.GBPAUD + data.GBPNZD + data.GBPCAD + data.GBPCHF + (100 - data.EURGBP))
    strength["CHF"] = 1 / 7 * ((100 - data.EURCHF) + (100 - data.GBPCHF) + (100 - data.NZDCHF) + (100 - data.AUDCHF) + (
                100 - data.CADCHF) + data.CHFJPY + (100 - data.USDCHF))
    strength["JPY"] = 1 / 7 * ((100 - data.EURJPY) + (100 - data.GBPJPY) + (100 - data.USDJPY) + (100 - data.CHFJPY) + (
                100 - data.CADJPY) + (100 - data.NZDJPY) + (100 - data.AUDJPY))
    strength["AUD"] = 1 / 7 * ((100 - data.EURAUD) + (100 - data.GBPAUD) + (
                100 - data.AUDJPY) + data.AUDNZD + data.AUDCAD + data.AUDCHF + data.AUDUSD)
    strength["CAD"] = 1 / 7 * (
                (100 - data.EURCAD) + (100 - data.GBPCAD) + (100 - data.USDCAD) + data.CADJPY + (100 - data.AUDCAD) + (
                    100 - data.NZDCAD) + data.CADCHF)
    strength["NZD"] = 1 / 7 * (
                (100 - data.EURNZD) + (100 - data.GBPNZD) + data.NZDJPY + data.NZDUSD + data.NZDCAD + data.NZDCHF + (
                    100 - data.AUDNZD))
    strength_df = strength.iloc[-strength_loc].apply(lambda x: x - 50).round(2).sort_values(ascending=False)

    return strength_df





def isvalid_signal_using_currency_strength(signal, currency_strengths):
    """
    Evaluates a buy/sell signal based on currency strength differences.

    Parameters:
        signal (str): The trading signal in the format 'EURUSD Buy' or 'EURUSD Sell'.
        currency_strengths (dict): A dictionary with currency codes as keys and their strengths as values.

    Returns:
        str: 'Valid' if the signal meets the criteria, 'Excluded' otherwise.
    """
    try:
        # Parse the signal
        pair, action = signal.split()
        base_currency = pair[:3]
        quote_currency = pair[3:]

        # Get strengths for the base and quote currencies
        base_strength = currency_strengths[base_currency]
        quote_strength = currency_strengths[quote_currency]

        if base_strength is None or quote_strength is None:
            return "Excluded: Invalid currency pair or missing strength data"

        # Calculate strength difference
        strength_diff = abs(base_strength - quote_strength)

        # Check criteria
        if (
                strength_diff > 10
                and ((base_strength > 0 > quote_strength) if action == "Buy" else (quote_strength > 0 > base_strength))
        ):
            return True
        else:
            return False
    except Exception as e:
        return f"Error: {str(e)}"




########################################################################################################################
#                                         Strategy Specific functions
########################################################################################################################





def calculate_williamsPCT_signals(df, period=g_willpct_period):
    """
    Generate buy and sell signals based on Williams %R indicator crossovers.

    This function calculates the Williams %R values for the given DataFrame
    and identifies buy and sell signals when the %R crosses key thresholds (-20 for overbought, -80 for oversold).
    Signals are stored in a new 'signal' column:
    1 for buy, -1 for sell, and 0 for no signal.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing 'High', 'Low', and 'Close' columns.
        period (int): The period for calculating the Williams %R indicator.

    Returns:
        pd.DataFrame: The input DataFrame with added columns for Williams %R values ('WPR') and signals ('signal').
    """
    # Calculate Williams %R
    df = calculate_williams_percent(df, period)

    # Create Signal column based on previous row's values including crossover logic
    df['signal'] = 0

    df.loc[(df['WPR'].shift(1) > -20) & (df['WPR'].shift(2) <= -20), 'signal'] = 1  # Buy signal
    df.loc[(df['WPR'].shift(1) < -80) & (df['WPR'].shift(2) >= -80), 'signal'] = -1  # Sell signal

    return df





def calculate_ma_trend_momentum_signals(df, fastMa=g_fast_ma, slowMA=g_slow_ma, ma_type=g_ma_type, williamsR=g_willpct_period):
    """
    Identify trend signals using exponential moving averages (EMA) and the Williams %R indicator.

    The function calculates two EMAs: a fast EMA and a slow EMA. Additionally, it uses the Williams %R
    momentum indicator to determine potential buy or sell signals. A buy signal is generated when the
    price is above both EMAs, and the Williams %R crosses above -20 from below. Conversely, a sell signal
    is generated when the price is below both EMAs, and the Williams %R crosses below -80 from above.

    Parameters:
        :param df: (pd.DataFrame): The input DataFrame containing 'close', 'high', and 'low' columns.
        :param fastMa: (int): The period for the fast EMA.
        :param slowMA: (int): The period for the slow EMA.
        :param ma_type: (str): To make ability to change MA type
        :param williamsR: The period for the williams %R momentum indicator.

    Returns:
        pd.DataFrame: Updated DataFrame including calculated 'Fast_MA', 'Slow_MA', 'Williams %R', and 'signal' columns.
                      The 'signal' column contains 1 -> buy signals, -1 -> Sell signals, and 0 for no signal.


    """
    # Calculate EMA
    df = calculate_moving_average(df, ma_type, period=fastMa)
    df = calculate_moving_average(df, ma_type, period=slowMA)

    # Calculate Williams %R
    df = calculate_williams_percent(df, williamsR)

    # Create Signal column based on previous row's values including crossover logic
    df['signal'] = 0

    for i in range(1, len(df)):
        # Buy signal
        df.loc[(df['Close'].shift(i + 1) > df[f"{ma_type}_{fastMa}"].shift(i + 1))
               & (df[f"{ma_type}_{fastMa}"].shift(i + 1) > df[f"{ma_type}_{slowMA}"].shift(i + 1))
               & (df['WPR'].shift(i + 1) > -20)
               & (df['WPR'].shift(i + 2) <= -20), 'signal'] = 1

        # Sell signal
        df.loc[(df['Close'].shift(i + 1) < df[f"{ma_type}_{fastMa}"].shift(i + 1))
               & (df[f"{ma_type}_{fastMa}"].shift(i + 1) < df[f"{ma_type}_{slowMA}"].shift(i + 1))
               & (df['WPR'].shift(i + 1) < -80)
               & (df['WPR'].shift(i + 2) >= -80), 'signal'] = -1

    return df






def calculate_willpct_swing_lines(df, williamsR=g_willpct_period):
    """
    Identify extreme points based on the Williams %R indicator.

    The function computes the Williams %R indicator for a given DataFrame
    and uses its movement to detect direction changes swingline direction based on extreme points.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing 'high', 'low', and 'close' columns.
        williamsR (int): The period for calculating the Williams %R indicator.

    Returns:
        pd.DataFrame: The input DataFrame with additional columns:
                      - 'Williams %R': The calculated Williams %R values.
                      - 'swingline': Indicates direction changes (1 for upward, -1 for downward).
    """

    # Calculate Williams %R
    df = calculate_williams_percent(df, williamsR)
    df['WPR'] = df['WPR'].shift(1)
    df['prev_WPR'] = df['WPR'].shift(1)

    # Calculate the Williams %R extremes and then the swingline direction
    df['swingline'] = np.select(
        [
            (df['WPR'] > -20) & (df['prev_WPR'] < -20),  # Condition for 1
            (df['WPR'] < -80) & (df['prev_WPR'] > -80)  # Condition for -1
        ],
        [1, -1],  # Values to assign (1 for the first condition, -1 for the second condition)
        default=np.nan  # Set default to NaN to allow forward filling later
    )

    df['swingline'] = df[
        'swingline'].ffill()  # Fill NaN values with the previous value (propagate values where conditions are not met)
    return df






def calculate_ltf_close_above_below_hft(ltf_df, htf_df):
    """
    This function aligns lower time frame (LTF) data with higher time frame (HTF) data
    to analyze the close price movement above or below previous HTF extremes.

    Parameters:
        ltf_df (pd.DataFrame): DataFrame containing lower time frame data.
        htf_df (pd.DataFrame): DataFrame containing higher time frame data.

    Returns:
        pd.DataFrame: Updated DataFrame with additional columns including swingline
                      and significant close alerts.
    """

    # Shift htf_df close to ensure we only compare to fully closed m5 bars
    htf_df['prev_High_HTF'] = htf_df['High'].shift(1)
    htf_df['prev_Low_HTF'] = htf_df['Low'].shift(1)

    # Merge the two DataFrames on their datetime index
    aligned_df = pd.merge(
        ltf_df, htf_df,
        how='outer',  # Use 'outer' to keep all timestamps from both DataFrames
        left_index=True,
        right_index=True,
        suffixes=('', '_htf')  # Add suffixes to differentiate columns from m1_df and m5_df
    )

    # Forward-fill missing values using `ffill` directly
    aligned_df.ffill(inplace=True)  # Forward-fill missing values in place

    aligned_df = aligned_df[["Open", "High", "prev_High_HTF", "Low", "prev_Low_HTF", "Close"]]

    df = aligned_df.copy()

    # Calculate the significant close and then the swingline direction
    df['swingline'] = np.select(
        [
            (df['Close'] > df['prev_High_HTF']) & (df['Close'] > df['open']),  # Condition for 1
            (df['Close'] < df['prev_Low_HTF']) & (df['Close'] < df['open'])  # Condition for -1
        ],
        [1, -1],  # Values to assign (1 for the first condition, -1 for the second condition)
        default=np.nan  # Set default to NaN to allow forward filling later
    )

    df['swingline'] = df[
        'swingline'].ffill()  # Fill NaN values with the previous value (propagate values where conditions are not met)

    return df





def calculate_swingline_alerts(df):
    """
    Determines significant alerts (swing reversals) based on changes in the swingline direction.

    Parameters:
        df (pd.DataFrame): DataFrame containing a 'swingline' column with directional values.

    Returns:
        pd.DataFrame: Updated DataFrame with an additional 'sig_alert' column indicating
                      swing reversal alerts (1 for upward reversal, -1 for downward reversal).
    """

    df['signal'] = np.select(
        [
            (df['swingline'] == 1) & (df['swingline'].shift(1) == -1),  # Condition for 1
            (df['swingline'] == -1) & (df['swingline'].shift(1) == 1)  # Condition for -1
        ],
        [1, -1],  # Values to assign (1 for the first condition, -1 for the second condition)
        default=0
    )

    return df






def calculate_fractal_pivot_points(df):
    """
    Identifies fractal pivot points in the DataFrame based on swingline directions.

    Parameters:
    df (pd.DataFrame): DataFrame containing a 'swingline' column, as well as 'high' and 'low' columns.

    Returns:
    pd.DataFrame: The input DataFrame with an added 'isPivot' column.
                  Each pivot point is marked as:
                  -1 for a low pivot (local minima) in a downward swing,
                   1 for a high pivot (local maxima) in an upward swing,
                   and NaN for non-pivot rows.
    """

    # Initialize 'isPivot' column with NaN
    df['isPivot'] = np.nan

    # Create groups of consecutive 'swingline' values
    group_ids = (df['swingline'] != df['swingline'].shift()).cumsum()
    groups = df.groupby(group_ids)

    # Iterate over each group
    for group_id, group_data in groups:
        sig_value = group_data['swingline'].iloc[0]

        if sig_value == -1:
            # Find index of the minimum 'low' in this group
            min_low_idx = group_data['Low'].idxmin()
            df.at[min_low_idx, 'isPivot'] = -1
        elif sig_value == 1:
            # Find index of the maximum 'high' in this group
            max_high_idx = group_data['High'].idxmax()
            df.at[max_high_idx, 'isPivot'] = 1

    return df
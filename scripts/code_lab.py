import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

import controller as ctrl
import trader as trd
import time


def testing_strategy():
    curr_strength = ctrl.calculate_currency_strength()
    print(f"Currency Strength: {curr_strength}\n")

    for symbol in ctrl.g_symbols_forex:
        df = ctrl.fetch_data(symbol, "M5", start_pos=ctrl.g_start_pos, end_pos=ctrl.g_end_pos)
        # signal = ctrl.random(symbol)
        # signal = ctrl.ma_trend_willpct_strategy(symbol, df)

        # ltf_df = ctrl.fetch_data(symbol, "M1", start_pos=ctrl.g_start_pos, end_pos=ctrl.g_end_pos)
        # signal = ctrl.market_structure_strategy(symbol, ltf_df, df)

        signal = ctrl.williams_percent_momentum_strategy(symbol, df)

        # signal = ctrl.double_bottom_top_strategy(symbol, df)

        print(signal)


def testing_risk():
    # Initialize PortfolioRiskMan with start and end dates
    end_date = datetime.strptime("2024-12-03", "%Y-%m-%d")
    start_date = (end_date - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    portfolio = ctrl.PortfolioRiskMan(start_date=start_date, end_date=end_date)
    # portfolio = ctrl.PortfolioRiskMan(start_position=ctrl.g_start_pos, end_position=ctrl.g_end_pos_d1)

    # Add positions to the portfolio
    portfolio.add_position('USDJPY', 0.04)  # long position with 1 lot size
    # portfolio.add_position('EURUSD', -1)  # short position with 1 lot size

    open_positions = len(portfolio.get_positions())
    curr_value_at_risk = portfolio.run()

    # Calculations of proposed positions
    pair = 'AUDNZD'
    action = 'Buy'
    d1_df = ctrl.fetch_data(pair, ctrl.g_core_timeframe, start_date=start_date, end_date=end_date)
    symbol_info = ctrl.mt5.symbol_info(pair)
    current_adr, current_daily_range_percentage, current_sl = ctrl.get_adr(d1_df, symbol_info)
    lots = ctrl.get_position_size(symbol_info, current_sl, max_risk_per_trade=5, risk_base_amount=300)
    lots = lots if action == "Buy" else -lots

    portfolio.add_position(pair, 0.14)
    print(portfolio.get_positions())

    proposed_value_at_risk = portfolio.run()

    if open_positions == 0:
        incr_var = 100
    else:
        incr_var = ((proposed_value_at_risk - curr_value_at_risk) / curr_value_at_risk) * 100

    str_message = (f"ADR: {current_adr} | "
                   f"SL: {current_sl} | "
                   f"Lots: {lots} |  "
                   f"Curr VAR ${round(curr_value_at_risk)} | "
                   f"Prop VAR ${round(proposed_value_at_risk)} | "
                   f"Diff VAR {round(incr_var)}% | ")
    print(str_message)

    # Get the optimized lot sizes based on the optimized portfolio weights
    # optimized_lot_sizes = portfolio.get_optimized_lot_sizes()
    # print(f"OPTIMIZED LOT SIZES: {optimized_lot_sizes}")


def filter_buy_sell_signals(df):
    """
    Creates a new DataFrame with 'buy' and 'sell' columns based on the given signal DataFrame.

    Parameters:
        df (pd.DataFrame): A DataFrame where the index is datetime, columns are symbols,
                           and values are 1 (buy), -1 (sell), or 0 (no signal).

    Returns:
        pd.DataFrame: A new DataFrame with 'buy' and 'sell' columns containing
                      the symbol names where signals occurred.
    """
    buy_sell_df = pd.DataFrame(index=df.index, columns=['buy', 'sell'])

    for index, row in df.iterrows():
        buy_symbols = row[row == 1].index.tolist()  # Get symbols where signal == 1
        sell_symbols = row[row == -1].index.tolist()  # Get symbols where signal == -1

        buy_sell_df.at[index, 'buy'] = ', '.join(buy_symbols) if buy_symbols else ''
        buy_sell_df.at[index, 'sell'] = ', '.join(sell_symbols) if sell_symbols else ''

    return buy_sell_df


if __name__ == '__main__':
    print("Starting trading bot.....\n")
    start_time = time.time()
    # current_account_info = ctrl.mt5.account_info()
    # print("------------------------------------------------------------------")
    # print(f"Login: {ctrl.mt5.account_info().login} \tserver: {ctrl.mt5.account_info().server}")
    # print(f"Date: {ctrl.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # print(
    #     f"Balance: {current_account_info.balance} USD, \t Equity: {current_account_info.equity} USD, \t Profit: {current_account_info.profit} USD")
    # print("------------------------------------------------------------------")

    # Initialize the OrderInfo object

    trade = trd.MT5Trade()

    if trade.is_connected():
        print("Successfully connected to MT5")
    else:   print("Failed to connect to MT5")

    #trade.sell("GBPUSD", 0.01, 10,10)
    trade.buy_limit("EURGBP", 0.01, 0.83925)




    # if positions == None:
    #     print("No positions on USDCHF, error code={}".format(ctrl.mt5.last_error()))
    # elif len(positions) > 0:
    #     print("Total positions on USDCHF =", len(positions))
    #     # display all open positions
    #     for position in positions:
    #         print(position)

    # display data on active orders on GBPUSD
    # orders = ctrl.mt5.orders_get()
    # if orders is None:
    #     print("No orders on GBPUSD, error code={}".format(ctrl.mt5.last_error()))
    # else:
    #     print("Total orders on GBPUSD:", len(orders))
    #     # display all active orders
    #     for order in orders:
    #         print(order)




    #testing_risk()
    #df = ctrl.fetch_data("AUDJPY", "M5", start_pos=ctrl.g_start_pos, end_pos=1000, amibroker=True)
    #df = ctrl.fetch_data("EURUSD", "M5", start_date="2025-02-16", end_date="2025-02-23")
    #df = ctrl.fetch_data("EURUSD", "M5", start_pos=ctrl.g_start_pos, end_pos=1000)
    #df = ctrl.calculate_moving_average(df)
    #df = ctrl.williams_percent_momentum_strategy_backtest("EURUSD", df)
    #df = ctrl.williams_percent_momentum_strategy("EURUSD", df)
    #print(df[df["signal"]!=0])
    #print(df.tail(25))

    # i = 1
    # for symbol in ctrl.g_symbols_forex:
    #     print(f"\nDownloading {symbol}... {i} of {len(ctrl.g_symbols_forex)}")
    #     df = ctrl.fetch_data(symbol, "M1", start_date="2023-01-01", end_date="2025-02-25", amibroker=True)
    #     i += 1




##################################################### TESTING ROW BY ROW SIGNAL ########################################

    # for i in range(1, len(df) + 1):
    #     partial_df = df.iloc[:i].copy()
    #     if len(partial_df) < 300:
    #         continue
    #
    #     curr_time, signal = ctrl.williams_percent_momentum_strategy("EURUSD", partial_df)
    #     print(f"{curr_time} Signal: {signal}")





##############################                TRADING                 #############################################

    #trade = ctrl.Trade()
    #trade.market_order("GBPUSD", 0.1, buy=True, sell=False, stop_loss_pips=10, take_profit_pips=10, slippage=20, magic_number=1988)
    #trade.pending_order("EURUSD", 0.2, "sell_limit", 1.051, stop_loss_pips=10, take_profit_pips=20,slippage=20, magic_number=1988)



    #result = trade.get_open_positions_and_orders()
    # print("Open Positions:")
    # print(result['positions'])
    # print("\nPending Orders:")
    # print(result['orders'])
    # print(result)

    #trade.close_order(131542931)
    #trade.close_all_positions()
    #trade.close_all_pending_orders()



########################################################################################################################


##############################                NOTIFICATION                 #############################################
   # # Example usage (this example would be replaced with your actual logic)
   # # Compose a sample message
   # formatted_message = sample_message = ctrl.compose_markdown_message(
   #     title="Trading Alert!",
   #     text="A new trade as been entered.",
   #     details={"Symbol": "EURUSD",
   #              "Action": "BUY",
   #              "Price": "1.2345"},
   #     code_blocks = {
   #         "python": "def hello_world():\n    print('Hello, World!')",
   #         "json": '{"key": "value"}'}
   # )
   #
   # # You can now use this formatted message with your send_telegram_alert function
   # ctrl.send_telegram_alert(message=formatted_message)

########################################################################################################################


##############################                LOGGER                 ###################################################
   # Example logging calls (for reference)
   # Test logging
   #ctrl.log_info("Moving Average Crossover", {"symbol": "EURUSD", "profit": 50})
   #ctrl.log_mt5_connection_failure("Unable to establish connection to MT5 server")
   #ctrl.log_trade_closed("Moving Average Crossover", {"symbol": "EURUSD", "profit": 50})
   #ctrl.log_critical_event("Data Feed Interruption", "Lost connection to price feed for 5 minutes")

   # General logging
   #ctrl.logger.debug("This is a debug message")
   #ctrl.logger.info("This is an info message")
   #ctrl.logger.warning("This is a warning message")
   #ctrl.logger.error("This is an error message")


########################################################################################################################


    ##################################################### GETTING SIGNALS ##############################################
    # data = pd.DataFrame()
    # for symbol in ctrl.g_symbols_forex:
    #     df = ctrl.fetch_data(symbol, "M5", start_date="2023-12-01", end_date="2025-01-01")
    #     df = ctrl.williams_percent_momentum_strategy_backtest(symbol, df)
    #     data[symbol] = df['signal']
    #
    # df = ctrl.fetch_data("XAUUSD", "M1", start_date="2023-12-01", end_date="2025-01-01")
    # data.to_csv("williams_percent_momentum_strategy_backtest-2024.csv")
    # print(data)

########################################################################################################################


    ##################################################### Average pips of a timeframe ##################################

    # end_date = datetime.now().strftime("%Y-%m-%d")
    # start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    #
    # df = ctrl.fetch_data("XAUUSD", "M5", start_date=start_date, end_date=end_date)
    # symbol_info = ctrl.mt5.symbol_info("XAUUSD")
    # ave_days = len(df) / 2
    # df["range"] = df["High"] - df["Low"]
    # df["roll_average"] = df["range"].rolling(int(ave_days)).mean()
    #
    # ave_pips = df["roll_average"].iloc[-1] / (symbol_info.trade_tick_value * 10)
    # print(ave_pips)


########################################################################################################################


##################################################### GETTING SL TARGETS ###############################################
    # data = pd.DataFrame()
    # for symbol in ctrl.g_symbols_forex:
    #     symbol_info = ctrl.mt5.symbol_info(symbol)
    #     d1_df = ctrl.fetch_data(symbol, "D1", start_date="2023-12-01", end_date="2025-01-01")
    #     current_adr = ctrl.get_adr(d1_df, symbol_info, ctrl.g_adr_period )
    #     data[symbol] = current_adr['SL']
    #
    # data.to_csv("SL_targets-2024.csv")
    # print(data)

    # for symbol in ctrl.g_symbols_forex:
    #     d1_df = ctrl.fetch_data(symbol, "D1", start_pos=0, end_pos=1000)
    #     symbol_info = ctrl.mt5.symbol_info(symbol)
    #     current_adr, current_daily_range_percentage, current_sl = ctrl.get_adr(d1_df, symbol_info, ctrl.g_adr_period)
        #d1_df['Over_ADR'] = (d1_df['daily_range'] > (1.5*d1_df['ADR'])).astype(int)
        #d1_df = d1_df.dropna()
        #d1_df.to_csv("testing.csv")

        #over_adr_percent = (len(d1_df[d1_df['Over_ADR']==1]) / len(d1_df)) * 100

        #print(f" {symbol}, ADR {current_adr} SL {current_sl}")


########################################################################################################################


##################################################### GETTING CURRENCY STRENGTHS ###################################################################

    #curr_strength = ctrl.calculate_currency_strength()
    #curr_strength.to_csv("currency_strength_Test.csv")
    #print(curr_strength)


##################################################### MERGING SIGNALS  and STRENGTH ####################################
    # df1 = pd.read_csv("currency_strength-2024.csv")
    # df2 = pd.read_csv("double_bottom_top_strategy_signals-2024.csv")
    # buy_sell_df = filter_buy_sell_signals(df2)
    #
    # merged_df = pd.concat([buy_sell_df, df1], axis=1)
    #
    # merged_df.set_index('datetime', inplace=True)
    #
    # merged_df.to_csv("buy_sell_signals.csv", index=True)
    # print(merged_df)

#######################################################################################################################
    #
    # # 1. Read the CSV
    # df_signals = pd.read_csv("williams_percent_momentum_strategy_backtest-2024.csv", index_col="DateTime", parse_dates=True)
    #
    # # 2. Create an empty result DataFrame with the same index and two columns: Buy and Sell
    # df_result = pd.DataFrame(index=df_signals.index, columns=["Buy", "Sell"])
    # df_result["Buy"] = ""
    # df_result["Sell"] = ""
    #
    # # 3. Iterate over each row in df_signals
    # for idx, row in df_signals.iterrows():
    #     buy_symbols = []
    #     sell_symbols = []
    #
    #     # For each symbol column, check if it's non-zero
    #     for col in df_signals.columns:
    #         value = row[col]
    #         if value == 1:
    #             buy_symbols.append(col)
    #         elif value == -1:
    #             sell_symbols.append(col)
    #
    #     # 4. Join the symbol lists into comma-separated strings
    #     df_result.at[idx, "Buy"] = ",".join(buy_symbols)
    #     df_result.at[idx, "Sell"] = ",".join(sell_symbols)
    #
    # # 5. Save results to a new CSV
    # df_result.to_csv("output_signals_2024.csv")

    print("\n......Main Ended. Bot Stopping.....!")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time} seconds")


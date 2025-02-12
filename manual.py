import controllers as ctrl

def testing_strategy():
    curr_strength = ctrl.calculate_currency_strength()
    print(f"Currency Strength: {curr_strength}")

    for symbol in ctrl.g_symbols_forex:
        df = ctrl.fetch_data(symbol, "M5", start_pos=ctrl.g_start_pos, end_pos=ctrl.g_end_pos)
        #signal = ctrl.random(symbol)
        #signal = ctrl.ma_trend_willpct_strategy(symbol, df)

        #ltf_df = ctrl.fetch_data(symbol, "M1", start_pos=ctrl.g_start_pos, end_pos=ctrl.g_end_pos)
        #signal = ctrl.market_structure_strategy(symbol, ltf_df, df)

        signal = ctrl.williams_percent_momentum_strategy(symbol, df)

        print(signal)


def testing_risk():

    # Initialize PortfolioRiskMan with start and end dates
    portfolio = ctrl.PortfolioRiskMan(start_position=ctrl.g_start_pos, end_position=ctrl.g_end_pos_d1)

    # Add positions to the portfolio
    portfolio.add_position('GBPUSD', 1)  # long position with 1 lot size
    portfolio.add_position('EURJPY', -1)  # long position with 1 lot size

    open_positions = len(portfolio.get_positions())
    curr_value_at_risk = portfolio.run()

    # Calculations of proposed positions
    d1_df = ctrl.fetch_data('EURJPY', ctrl.g_core_timeframe, start_date=ctrl.g_start_date, end_date=ctrl.g_end_date)
    symbol_info = ctrl.mt5.symbol_info('EURJPY')
    current_adr, current_daily_range_percentage = ctrl.get_adr(d1_df, symbol_info)
    lots = ctrl.get_position_size(current_adr / ctrl.g_stop_adr_ratio, ctrl.g_max_risk_per_trade,
                                  ctrl.g_risk_base_amount,
                                  symbol_info.trade_tick_value)

    portfolio.add_position('CADCHF', -1)

    proposed_value_at_risk = portfolio.run()

    if open_positions == 0:
        incr_var = 100
    else:
        incr_var = ((proposed_value_at_risk - curr_value_at_risk) / curr_value_at_risk) * 100

    str_message = (f"ADR: {current_adr / 10} | "
                   f"SL: {round(current_adr / 30)} | "
                   f"Lots: {lots} |  "
                   f"Curr VAR ${round(curr_value_at_risk)} | "
                   f"Prop VAR ${round(proposed_value_at_risk)} | "
                   f"Diff VAR {round(incr_var)}% | ")
    print(str_message)

    # Get the optimized lot sizes based on the optimized portfolio weights
    # optimized_lot_sizes = portfolio.get_optimized_lot_sizes()
    # print(f"OPTIMIZED LOT SIZES: {optimized_lot_sizes}")


if __name__ == '__main__':
    print("Starting trading bot.....\n")
    start_time = ctrl.time.time()
    current_account_info = ctrl.mt5.account_info()
    print("------------------------------------------------------------------")
    print(f"Login: {ctrl.mt5.account_info().login} \tserver: {ctrl.mt5.account_info().server}")
    print(f"Date: {ctrl.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        f"Balance: {current_account_info.balance} USD, \t Equity: {current_account_info.equity} USD, \t Profit: {current_account_info.profit} USD")
    print("------------------------------------------------------------------")


    df = ctrl.fetch_data("GBPJPY", "M5", start_pos=ctrl.g_start_pos, end_pos=1000)

    for i in range(1, len(df) + 1):
        partial_df = df.iloc[:i].copy()
        if len(partial_df) < 300:
            continue

        signal = ctrl.williams_percent_momentum_strategy("GBPJPY", partial_df)
        print(f"Signal: {signal}")
    # df =  ctrl.williams_percent_momentum_strategy("GBPJPY", df)
    # print(df.tail())

    #testing_strategy()
    # curr_strength = ctrl.calculate_currency_strength()
    # print(f"Currency Strength: \n{curr_strength}")


    print("\n......Main Ended. Bot Stopping.....!")
    end_time = ctrl.time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time} seconds")
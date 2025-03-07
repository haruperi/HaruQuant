import json

import controller as ctrl

def live_run():
    token = ctrl.g_token
    chat_id = ctrl.g_chat_id

    curr_strength = ctrl.calculate_currency_strength()

    for symbol in ctrl.g_symbols_forex:
        symbol_info = ctrl.mt5.symbol_info(symbol)

        # Validate the symbol_info object
        if not symbol_info or not hasattr(symbol_info, "trade_tick_size"):
            print(f"Error: Invalid symbol_info for {symbol}. Skipping...")
            continue

        df = ctrl.fetch_data(symbol, "M5", start_pos=ctrl.g_start_pos, end_pos=ctrl.g_end_pos)
        curr_time, signal = ctrl.williams_percent_momentum_strategy(symbol, df)

        if signal != f"{symbol} Neutral":
            d1_df = ctrl.fetch_data(symbol, "D1", start_pos=ctrl.g_start_pos, end_pos=ctrl.g_end_pos_d1)

            current_adr, current_daily_range_percentage, current_sl = ctrl.get_adr(d1_df, symbol_info)
            lots = ctrl.get_position_size(symbol_info, current_sl)

            curr_value_at_risk = 0
            open_positions = 0
            portfolio = ctrl.PortfolioRiskMan()

            # Get the current open positions
            positions = ctrl.mt5.positions_get()
            # Check if there are any open positions
            if positions is not None or len(positions) != 0:
                # Iterate through the positions and save them to the dictionary
                for position in positions:
                    vol_lots = -position.volume if position.type == 1 else position.volume
                    portfolio.add_position(position.symbol, vol_lots)
                    open_positions = open_positions + 1

                curr_value_at_risk = portfolio.run()

            pair, action = signal.split()
            lots = lots if action == "Buy" else -lots
            portfolio.add_position(pair, lots)
            proposed_value_at_risk = portfolio.run()
            if open_positions == 0:
                incr_var = 100
            else:
                incr_var = ((proposed_value_at_risk - curr_value_at_risk) / curr_value_at_risk) * 100

            # str_message = (f"{curr_time} | "
            #                f"{pair} -> ADR: {current_adr} | "
            #                f"Range: {current_daily_range_percentage}% | "
            #                f"SL: {current_sl} | "
            #                f"Lots: {lots} |  "
            #                f"Curr VAR ${round(curr_value_at_risk)} | "
            #                f"Prop VAR ${round(proposed_value_at_risk)} | "
            #                f"Diff VAR {round(incr_var)}% | "
            #                f"Signal: {action}\n")

            # Send message to Telegram
            str_message = {
                "Time": curr_time,
                "Symbol": pair,
                "Signal": action,
                "ADR": current_adr,
                "Range": current_daily_range_percentage,
                "SL": current_sl,
                "Lots": lots,
                "CurrVAR": f"${round(curr_value_at_risk):,.2f}",
                "PropVAR": f"${round(proposed_value_at_risk):,.2f}",
                "DiffVAR": f"{round(incr_var)}%",
            }

            formatted_message = ctrl.compose_markdown_message(
                title="Trading Signal Alert!",
                text="Proposed Trades...",
                details={},
                code_blocks={"json": f"{json.dumps(str_message, indent=4, default=str)}"},
            )

            ctrl.send_telegram_alert(message=formatted_message)

            print(str_message)
    print(curr_strength)
    print("\n\n\n")


if __name__ == '__main__':
    while True:
        ctrl.countdown_to_next_bar()
        live_run()

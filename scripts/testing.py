import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from math import log, sqrt, exp
from scipy.stats import norm
import controller as ctrl


def simple_martingale_simulation(starting_balance, base_bet_percentage, win_rate, days):
    balance = starting_balance
    results = []

    for day in range(1, days + 1):
        daily_balance = balance
        current_bet = daily_balance * base_bet_percentage  # Calculate bet as a percentage of the current balance
        while True:
            # Simulate the outcome of a round: win or loss
            outcome = random.random() < win_rate  # win_rate is the probability of a win

            if outcome:  # Win
                daily_balance += current_bet
                break  # Stop after a win
            else:  # Loss
                daily_balance -= current_bet
                if daily_balance <= 0:  # If balance is zero or negative, stop for the day
                    daily_balance = 0
                    break
                current_bet = min(daily_balance * base_bet_percentage,
                                  daily_balance)  # Adjust bet to a percentage of the remaining balance

        balance = daily_balance  # Update the main balance with daily outcome
        results.append(daily_balance)

        # Stop the simulation early if balance reaches 0
        if balance == 0:
            break

    return results, balance


def revert_martingale_simulation(starting_balance, base_bet_percentage, win_rate, days):
    balance = starting_balance
    results = []

    for day in range(1, days + 1):
        daily_balance = balance
        current_bet = daily_balance * base_bet_percentage  # Bet as a percentage of current balance
        consecutive_wins = 0

        while True:
            # Simulate the outcome of a round: win or loss
            outcome = random.random() < win_rate  # win_rate is the probability of a win

            if outcome:  # Win
                daily_balance += current_bet
                consecutive_wins += 1
                if consecutive_wins == 3:  # 3 consecutive wins
                    break
                current_bet = daily_balance * base_bet_percentage  # Double the bet after a win, but as a percentage of current balance
            else:  # Loss
                daily_balance -= current_bet
                consecutive_wins = 0
                if daily_balance <= 0:  # If balance is zero or negative, stop for the day
                    daily_balance = 0
                    break
                current_bet = daily_balance * base_bet_percentage  # Reset bet to base bet after a loss

        balance = daily_balance  # Update the main balance with daily outcome
        results.append(daily_balance)

        # Stop the simulation early if balance reaches 0
        if balance == 0:
            break

    return results, balance


def run_martingale_simulation():
    # Parameters
    starting_balance = 1000  # Starting balance
    base_bet_percentage = 0.001  # Base bet as 0.1% of the current balance
    win_rate = 0.5  # Win rate (50%)
    days = 20160  # Total number of days to simulate
    num_simulations = 1000  # Number of simulations to run

    # Simulate multiple runs and plot each result
    plt.figure(figsize=(10, 6))

    below_starting_balance_count = 0  # Counter for the number of simulations where balance falls below the starting balance

    for i in range(num_simulations):
        #results, final_balance = simple_martingale_simulation(starting_balance, base_bet_percentage, win_rate, days)
        results, final_balance = revert_martingale_simulation(starting_balance, base_bet_percentage, win_rate, days)
        plt.plot(results)

        # Check if the final balance is below the starting balance
        if final_balance < starting_balance:
            below_starting_balance_count += 1

    plt.title('Equity Chart of Simple Martingale Simulation (1000 Runs)')
    plt.xlabel('Days')
    plt.ylabel('Balance')
    plt.grid(True)
    #plt.legend()
    plt.show()

    # Print the number of simulations where balance fell below the starting balance
    print(f"Number of simulations where balance fell below the starting balance: {below_starting_balance_count}")

###################################################################################################################################


if __name__ == "__main__":
    #run_martingale_simulation()

    # -------------------------------
    # 1. Load Historical Data
    # -------------------------------

    data = pd.DataFrame()

    symbols = ["EURUSD", "USDCHF"]

    for symbol in symbols:
        df = ctrl.fetch_data(symbol, "D1", start_pos=0, end_pos=1000)



    df = data.copy()

    # -------------------------------
    # 2. Calculate Daily Returns
    # -------------------------------

    # Calculate daily percentage returns
    df["EURUSD_Return"] = df["EURUSD"].pct_change()
    df["USDCHF_Return"] = df["USDCHF"].pct_change()

    # Drop the first row (NaN returns)
    df = df.dropna().reset_index(drop=True)

    # -------------------------------
    # 3. Compute a Rolling Hedge Ratio (Beta)
    # -------------------------------

    # We use a rolling window to compute beta, which will be our hedge ratio.
    # Beta = Cov(returns_EURUSD, returns_USDCHF) / Var(returns_USDCHF)
    window = 20  # e.g. 20 trading days

    rolling_cov = df["EURUSD_Return"].rolling(window).cov(df["USDCHF_Return"])
    rolling_var = df["USDCHF_Return"].rolling(window).var()
    df["Hedge_Ratio"] = rolling_cov / rolling_var

    # For days where the window isn't available, we can forward-fill the beta
    df["Hedge_Ratio"].fillna(method="bfill", inplace=True)

    # -------------------------------
    # 4. Simulate the Hedged Portfolio
    # -------------------------------

    # Assume:
    # - You are long 1 lot of EUR/USD CFD (exposure = +1 lot)
    # - You hedge by shorting "hedge_ratio" lots of USD/CHF CFD.
    # - We assume each lot has a notional value (e.g., $100,000). For simplicity, we work with returns.

    # We'll calculate daily PnL for each leg.
    # PnL_leg = Position (in lots) * Notional * Return

    notional = 100000  # dollars per lot

    # Position sizes (in lots)
    df["EURUSD_Position"] = 1.0  # always long 1 lot
    df["USDCHF_Position"] = -df["Hedge_Ratio"]  # hedge leg: short beta lots

    # Daily PnL (in dollars)
    df["EURUSD_PnL"] = df["EURUSD_Position"] * notional * df["EURUSD_Return"]
    df["USDCHF_PnL"] = df["USDCHF_Position"] * notional * df["USDCHF_Return"]

    # Total hedged portfolio PnL is the sum of both legs
    df["Total_PnL"] = df["EURUSD_PnL"] + df["USDCHF_PnL"]

    # Cumulative PnL
    df["Cumulative_PnL"] = df["Total_PnL"].cumsum()

    # -------------------------------
    # 5. Visualize the Results
    # -------------------------------
    plt.figure(figsize=(12, 6))
    plt.plot(df["Date"], df["Cumulative_PnL"], label="Hedged Portfolio Cumulative PnL")
    plt.title("Dynamic Hedge Backtest (EUR/USD hedged with USD/CHF)")
    plt.xlabel("Date")
    plt.ylabel("PnL (USD)")
    plt.legend()
    plt.grid(True)
    plt.show()

    # Optional: Look at the first few rows of the DataFrame
    print(df.head(25))


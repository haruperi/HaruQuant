# Patch telegram.error to provide necessary attributes for vectorbt
import sys
import types

if "telegram.error" not in sys.modules:
    telegram_error = types.ModuleType("telegram.error")
    telegram_error.Unauthorized = Exception  # Dummy exception
    telegram_error.ChatMigrated = Exception  # Dummy exception
    sys.modules["telegram.error"] = telegram_error


import numpy as np
import pandas as pd
import yfinance as yf
import vectorbt as vbt
from itertools import product
import seaborn as sns
import matplotlib.pyplot as plt

# Function to calculate Commodity Channel Index (CCI)
def calculate_cci(df, period):
    tp = (df['High'] + df['Low'] + df['Close']) / 3  # Typical Price
    ma = tp.rolling(window=period).mean()
    md = (tp - ma).abs().rolling(window=period).mean()
    cci = (tp - ma) / (0.015 * md)
    return cci

# Function to calculate Vortex Indicator (VI)
def calculate_vortex(df, period):
    tr = np.maximum(df['High'] - df['Low'],
                    np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    vm_plus = abs(df['High'] - df['Low'].shift(1))
    vm_minus = abs(df['Low'] - df['High'].shift(1))
    vi_plus = vm_plus.rolling(window=period).sum() / tr.rolling(window=period).sum()
    vi_minus = vm_minus.rolling(window=period).sum() / tr.rolling(window=period).sum()
    return vi_plus, vi_minus


# Define the stock symbol and time period
symbol = 'WMT'  # Example stock symbol
start_date = '2019-01-01'
end_date = '2025-01-01'

# Download historical data
df = yf.download(symbol, start=start_date, end=end_date)
df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']

# Define parameter ranges
cci_periods = range(5, 51)  # Test CCI periods from 5 to 50
vortex_periods = range(5, 51)  # Test Vortex periods from 5 to 50

# Store results
results = []

# Iterate over all parameter combinations
for cci_p, vortex_p in product(cci_periods, vortex_periods):
    df['CCI'] = calculate_cci(df, period=cci_p)
    df['VI+'], df['VI-'] = calculate_vortex(df, period=vortex_p)

    # Define Entry and Exit signals
    df['Entry'] = ((df['CCI'] > 100) & (df['VI+'] > df['VI-'])) | ((df['CCI'] < -100) & (df['VI-'] > df['VI+']))
    df['Exit'] = ((df['VI+'] < df['VI-']) & (df['CCI'] > 0)) | ((df['VI-'] < df['VI+']) & (df['CCI'] < 0))

    # Filter data for backtesting (2020-2025)
    df_filtered = df[(df.index.year >= 2020) & (df.index.year <= 2025)]

    # Run backtest
    portfolio = vbt.Portfolio.from_signals(
        close=df_filtered['Close'],
        entries=df_filtered['Entry'],
        exits=df_filtered['Exit'],
        init_cash=100_000,
        fees=0.001
    )

    # Store performance metrics
    stats = portfolio.stats()
    total_return = stats.loc['Total Return [%]']

    results.append((cci_p, vortex_p, total_return))


# Convert results to DataFrame
results_df = pd.DataFrame(results, columns=['CCI Period', 'Vortex Period', 'Total Return'])

# Find best parameter set based on highest Total Return [%]
best_params = results_df.sort_values(by='Total Return', ascending=False).iloc[0]

print("Best Parameters:")
print(best_params)
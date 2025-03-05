import controller as ctrl
import datetime
import pandas as pd
from backtesting import Backtest
from backtesting import Strategy
from backtesting.lib import crossover, resample_apply

import matplotlib.pyplot as plt
import seaborn as sns

def optim_func(series):
    if series['# Trades'] < 10:
        return -1
    else:
        return series['Equity Final [$]']/series['Exposure Time [%]']

def SMA(values, n):
    """
    Return simple moving average of `values`, at
    each step taking into account `n` previous values.
    """
    return pd.Series(values).rolling(n).mean()

def RSI(array, n):
    """Relative strength index"""
    # Approximate; good enough
    gain = pd.Series(array).diff()
    loss = gain.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    rs = gain.ewm(n).mean() / loss.abs().ewm(n).mean()
    return 100 - 100 / (1 + rs)


class SmaCross(Strategy):
    # Define parameters as class variables
    n1 = 10
    n2 = 20
    d_rsi = 30  # Daily RSI lookback periods
    w_rsi = 30  # Weekly
    level = 70

    def init(self):
        # # Precompute the two moving averages
        # self.sma1 = self.I(SMA, self.data.Close, self.n1)
        # self.sma2 = self.I(SMA, self.data.Close, self.n2)

        # Compute moving averages the strategy demands
        self.ma10 = self.I(SMA, self.data.Close, 10)
        self.ma20 = self.I(SMA, self.data.Close, 20)
        self.ma50 = self.I(SMA, self.data.Close, 50)
        self.ma100 = self.I(SMA, self.data.Close, 100)

        # Compute daily RSI(30)
        self.daily_rsi = self.I(RSI, self.data.Close, self.d_rsi)

        # To construct weekly RSI, we can use `resample_apply()`
        # helper function from the library
        self.weekly_rsi = resample_apply(
            'h', RSI, self.data.Close, self.w_rsi)

    def next(self):
        # # If sma1 crosses above sma2, close any existing
        # # short trades, and buy the asset
        # if crossover(self.sma1, self.sma2):
        #     self.position.close()
        #     self.buy()
        #
        # # Else, if sma1 crosses below sma2, close any existing
        # # long trades, and sell the asset
        # elif crossover(self.sma2, self.sma1):
        #     self.position.close()
        #     self.sell()

        price = self.data.Close[-1]

        # If we don't already have a position, and
        # if all conditions are satisfied, enter long.
        if (not self.position and
                self.daily_rsi[-1] > self.level and
                self.weekly_rsi[-1] > self.level and
                self.weekly_rsi[-1] > self.daily_rsi[-1] and
                self.ma100[-1] < self.ma50[-1] < self.ma20[-1] < self.ma10[-1] < price):

            # Buy at market price on next open, but do
            # set 8% fixed stop loss.
            self.buy(sl=.92 * price)

        # If the price closes 2% or more below 10-day MA
        # close the position, if any.
        elif price < .98 * self.ma10[-1]:
            self.position.close()


if __name__ == '__main__':
    # df = ctrl.fetch_data("EURUSD", "M5", start_date="2025-02-16", end_date="2025-02-23")
    data = ctrl.fetch_data("EURUSD", "M5", start_pos=ctrl.g_start_pos, end_pos=1000)

    bt = Backtest(data, SmaCross, cash=10_000, commission=.002)

    # 1. Run the strategy
    stats = bt.run()

    # 2. Optimize the strategy parameters using a grid search
    # stats = bt.optimize(n1=range(5, 30, 5),
    #                     n2=range(10, 70, 5),
    #                     maximize='Equity Final [$]',
    #                     constraint=lambda param: param.n1 < param.n2)
    #                     max_tries = 100                 # Random Grid search

    # 3. Customize the strategy parameters using a custom optimization function
    # stats = bt.optimize(n1=range(5, 30, 5),
    #                     n2=range(10, 70, 5),
    #                     maximize=optim_func,
    #                     constraint=lambda param: param.n1 < param.n2)

    # 4. Plot the optimized strategy results using a heatmap
    # stats, heatmap  = bt.optimize(n1=range(5, 30, 5),
    #                     n2=range(10, 70, 5),
    #                     maximize=optim_func,
    #                     constraint=lambda param: param.n1 < param.n2,
    #                     return_heatmap = True)
    #
    # hm = heatmap.groupby(["n1", "n2"]).mean().unstack()
    # sns.heatmap(hm, cmap="plasma")
    # plt.show()

    # 5. Plot the strategy results using Matplotlib
    bt.plot()
    print(stats)
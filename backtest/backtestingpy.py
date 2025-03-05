import controller as ctrl
import datetime
import pandas as pd
from backtesting import Backtest
from backtesting import Strategy
from backtesting.lib import crossover

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


class SmaCross(Strategy):
    # Define parameters as class variables
    n1 = 10
    n2 = 20

    def init(self):
        # Precompute the two moving averages
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        # If sma1 crosses above sma2, close any existing
        # short trades, and buy the asset
        if crossover(self.sma1, self.sma2):
            self.position.close()
            self.buy()

        # Else, if sma1 crosses below sma2, close any existing
        # long trades, and sell the asset
        elif crossover(self.sma2, self.sma1):
            self.position.close()
            self.sell()

if __name__ == '__main__':
    # df = ctrl.fetch_data("EURUSD", "M5", start_date="2025-02-16", end_date="2025-02-23")
    data = ctrl.fetch_data("EURUSD", "M5", start_pos=ctrl.g_start_pos, end_pos=1000)

    bt = Backtest(data, SmaCross, cash=10_000, commission=.002)

    # 1. Run the strategy
    #stats = bt.run()

    # 2. Optimize the strategy parameters using a grid search
    # stats = bt.optimize(n1=range(5, 30, 5),
    #                     n2=range(10, 70, 5),
    #                     maximize='Equity Final [$]',
    #                     constraint=lambda param: param.n1 < param.n2)

    # 3. Customize the strategy parameters using a custom optimization function
    stats = bt.optimize(n1=range(5, 30, 5),
                        n2=range(10, 70, 5),
                        maximize=optim_func,
                        constraint=lambda param: param.n1 < param.n2)
    bt.plot()
    print(stats)
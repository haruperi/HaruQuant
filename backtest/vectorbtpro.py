import vectorbtpro as vbt


from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import controller as ctrl


if __name__ == '__main__':
    #data = ctrl.fetch_data("EURUSD", "M5", start_pos=ctrl.g_start_pos, end_pos=5000)
    #df = ctrl.williams_percent_momentum_strategy("EURUSD", df)
    #df = vbt.Data.from_data(data)

    #print(df)

    data = vbt.BinanceData.pull('BTCUSDT')



    print(data)
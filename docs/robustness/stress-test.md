# Stress Test

This phase uses statistical methods to abuse the strategy and see how fragile it is. It helps determine if the strategy's success is due to skill or luck.

### Trades cost test:

Simulates the effect of Spread/slippage/commission/swap (the difference between the expected price of a trade and the price at which the trade is actually executed). This is essential to ensure transaction costs don't erase your profits. Do these tests individually, then all at once after. For values to use, refer to the maximum values from the MT5 dataframes, which span 20 years.

**Copy all settings from the previous stage (if in custom projects)**

- In **Data** -> **Test Parameters** -> **Commission & Swap** ( ***set***: Current or Max Value of all symbols)
- In **Data** -> **Test Parameters** -> **Spread** ( ***set***: Max Value)
- In **Data -> Test Parameters -> Slippage** (set: 5 pips for forex and 20 for gold or Max Value)
- **In Data -> Backtest Data Settings -> Start day / End day** (set: time period pre-test + builder data)

![Slippage Settings](/img/stress-test-1.png)

- **In Ranking -> Strategy Filtering conditions** -> (set: Profit Factor (IS) > 1.1, Ret/DD Ratio (IS) > 0.5 per year, multiply with # of years )

![Ranking Settings](/img/stress-test-2.png)

### Monte Carlo and how it works?

- It is a statistical test
- It performs X simulations (Ideally 200)
- Then reliable values for the level specified are calculated
- For example, if we have a level of 95%, it means that 95% of the simulations had the specified or better results
- It gives us information about which strategy parameters we can trust

### MC Randomise trades order exact method

If exact trades appeared, but in a different order. Shuffles the order of your executed trades. If performance changes drastically, it may indicate a dependency on winning or losing streaks that might not occur in the future.

**Copy all settings from the build stage**

- **In Cross Checks (Robustness) -> Monte Carlo trades manipulation**
- **Set** : Randomise trades order, with method Exact, Number of Simulations 200
- **Filtering** -> Add Conditions ->
  - **Ret/DD Ratio** : From Backtest: Monte Carlo Trades manipulation: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 50)

### MC Randomise trades order resampling method

Randomly arrange, duplicate and delete some trades

**Copy all settings from the build stage**

- **In Cross Checks (Robustness) -> Monte Carlo trades manipulation** -> (set: Randomise trades order, with method Resampling, Number of Simulations 200, Filtering -> Add Conditions -> Ret/DD Ratio (From Backtest: Monte Carlo Trades manipulation: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 25) ))

### MC Randomly skip trades

If you trade with different brokers, some trades might be missed, so in this tests, randomly delete 10% of the trades. Deletes a random percentage of trades to see if the performance depends on a few lucky outlier trades.

**Copy all settings from the previous stage**

- **In Cross Checks (Robustness) -> Monte Carlo trades manipulation** -> (uncheck previous setting and set: Randomly skip trades with probability 10%, Number of Simulations 200, Filtering -> Add Conditions -> Ret/DD Ratio (From Backtest: Monte Carlo Trades manipulation: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 50) ))

### MC Randomize strategy parameters

How sensitive the strategy is to changing parameters within a certain range. Slightly changes your optimized parameters to see if performance falls apart. A robust strategy should still be profitable with slightly different settings.
In this test manually observe as well and further delete trades which passed but have big differences for example double number of trades or stagnant (sideways)

**Copy all settings from the previous stage**

- **In Cross Checks (Robustness) -> Monte Carlo retest methods** -> (set: Randomize strategy parameters, with probability 20 % and max change 30%, Number of Simulations 200, Filtering -> Add Conditions -> Ret/DD Ratio (From Backtest: Monte Carlo retest methods: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 50) ))

### MC Randomize history data

How sensitive the strategy is to differences in volatility of different brokers, for example, a candle in one broker might be a 20% candle in another broker. Checks if your strategy's performance is overly dependent on the specific path the market took. It shuffles the price bars to see if the edge disappears.

**Copy all settings from the previous stage**

- **In Data -> Test Parameters -> Precision** (set: Selected timeframe only)
- **In Cross Checks (Robustness) -> Monte Carlo retest methods** -> (set: Randomize history data, with probability 30 % and max price change 10 % of ATR, Number of Simulations 200, Filtering -> Add Conditions -> Ret/DD Ratio (From Backtest: Monte Carlo retest methods: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 50) ))

### MC Randomize slippage and spread

How sensitive the strategy is to differences in volatility of different brokers, for example, a candle in one broker might be a 30% candle in another broker.

**Copy all settings from the previous stage**

- **In Data -> Test Parameters -> Precision** (set: 1 minute data tick simulation)
- **In Cross Checks (Robustness) -> Monte Carlo retest methods** -> (set: . Randomize slippage from 0 to 5, Number of Simulations 10, Filtering -> Add Conditions -> Ret/DD Ratio (From Backtest: Monte Carlo retest methods: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 50)))

**Then Next test** (set: , Randomize spread from 0 to 5)

### MC Overall

Combine the above like in real life

**Copy all settings from the previous stage**

- **In Data -> Test Parameters -> Precision** (set: Selected timeframe only)
- **In Cross Checks (Robustness) -> Monte Carlo retest methods** -> (set: Randomize history data, with probability 10 % and max price change 10 % of ATR, set: Randomize slippage from 0 to 5, set: . Randomize spread from 1 to 5, Number of Simulations 200, Filtering -> Add Conditions -> Ret/DD Ratio (From Backtest: Monte Carlo retest methods: Confidence Level 95 >= Ret/ DD ( Apply percentage ratio: 50)))

### Filtering correlated strategies

**Copy all settings from the previous stage**

- **In Data -> Test Parameters -> Precision** (set: 1 minute data tick simulation)
- **In Cross Checks (Robustness) -> Monte Carlo retest methods** -> (set: off)
- **Filtering similar strategies, delete those with similar Ret/DD ratio** (manually check equity graphs )
- **Select all strategies**
- **Click create portfolio.**
- **Check portfolio correlation (Monthly, Profit/Loss)**

### Risk Tolerance Test

- **Trade using actual money management that will be used in live trading**
- **Risk tolerance per pair 10%**

### Out of Sample OOS2 (Post test data)

This is to make sure everything we ran above is valid

**Copy all settings from the build stage**

- **In Data -> Test Parameters -> Precision** (set: 1 minute data tick simulation)
- **In Data -> Backtest Data Settings -> Start day / End day** (set: time period post the period used in builder)
- **In Cross Checks (Robustness)** -> (uncheck: Retest with higher precision)
- **In Ranking -> Strategy Filtering conditions** -> (set: Profit Factor (IS) > 1.1, Ret/DD Ratio (IS) > 0.3 per year, multiply with # of years , check: Delete FAILED strategies from Databank)

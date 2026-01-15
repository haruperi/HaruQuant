# Robustness Overview

- Robustness is a measure of strategy strength that will indicate if the future live strategy performance metrics will match its performance in the back testing phase.
- A proper development process is critical to reach a conclusion about a strategy robustness.
- Robustness will eliminate doubts about trading the strategy with real money and give confidence in its forecasted performance.
- Regardless of the methodology to develop robust strategies, there is no guarantee that the output will be robust.
- Currently there is no retail platform that can run the full spectrum of robustness analysis on auto, but with some compromises it can be done with SQX.
- There is a skill that has to be learned in order to be able to run a full robustness analysis
- Only a portfolio of robust strategies will give you the highest probability that you will have a profitable outcome when going live.
- **Perform Robustness Checks**: The document lists three methods to verify your strategy's strength:
    - Walk Forward optimization.
    - SPP (System Parameter Permutation) tests.
- **Make the Final Verdict**: Based on the results of these tests, decide if the strategy is robust enough for live trading.

## Manual Guidelines
- Use all data, leave Hold Out Period that cover same market regimes in testing
- Longer look back periods (longer holding periods) usually leads to stable strategies that works on many correlated markets
- Short term look back periods strategy edges don’t last long, if your strategy including filters are trading all market regimes, then shorten the hold out period
- Don’t layer too many filters
- Add each layer separately as they should add significant improvements
- Use a fixed number for Stop Loss, Profit Target, use 2-4 ATR(10)
- Stop loss should be thought in terms of protecting capital and not enhancing strategy, and it should not be the reason for profitable strategy.
- Profit target is only good in short term mean reversion strategies and they will hurt the longer term strategies.
- Don’t try to optimize Strategy Filters lookback periods, they should either work or not. If they affect small number of losing trades then that’s not a good sign.
- If you are using WFM or SPP, then don’t optimize Strategy Filters, Stop Loss or Profit Target, but optimize only the parameters that will have the highest impact on strategy performance

## PERFORMANCE REVIEW

### Net Profit
- You want as big as possible relative to the instrument, number of trades, capital required and drawdown
- Small number is still ok if you have other good metrics.
    - You can always increase by position sizing.
    - Less exposure in the market will leave space for capital to be used in other strategies.
- Uniform distribution
- Avg & Med Trade > 2.5 x (Slipp+Comm)
- Number of Trades > 350
- Profit Factor > 1.2
- CAGR > 20% , (AR% / ADD%) > 2

### Drawdown
- We want the lowest maximum drawdown possible
- Look at the number of drawdowns, average drawdown amount and the median drawdown amount
- How long it took to get back to new highs (stagnation)
- Drawdown is linked to Net Profit, so always look at return to drawdown ratio, trade higher Ret/DD ratio strategies
- Always expect higher drawdown than back tested numbers
- %DD will depend on starting capital, while $DD will always be the same for fixed contract
- Stagnation < 1 Year (Swing), 1 Week (Intraday)
- Avg & Med DD < 0.5 x Max DD
- Consecutive Losers < 10

### Trades
- You are always looking for higher number of trades
- Small number of trades, will tie your capital and resources, so it has to add a lot of value
- Average trade should be at least 2.5 times (slippage & commission) to cover any strategy shocks.
- Median trade should be high close to average trade to eliminate outliers
- Median - 1 Standard Deviation preferably above zero
- Average trade > 10% of ATR100 for intraday strategies
- low number of bars in trades is better for lower exposure to market risk

### Periodical Returns
- Look for clean distribution of profits, consistently profitable with low losing years.
- Usually after an outlier positive year, the market will be quiet, and you have to expect that
- Median should be above zero, and preferably all years within 1 standard deviation of median.
- Look for smooth equity curve trending up (hard to get)
- Look for low stagnation periods
- Uniform distribution of profits
- 70% profitable years
- Discount Outlier performance
- Look for Stable/Up trend for the most recent years (3-6)
- Equity curve trending up

### Outliers
- They are not good positive or negative in any metric
- If they exist in a good strategy then discount their additions to the strategy metric
    - If after discounting their number the strategy metrics looks much worse then drop the strategy or look for strategy filter to boost all metrics
- If they happen in live trading, expect much lower numbers than median in the following period

### Trends
- While long historical back testing is important, always focus on the recent 3-6 years metrics.
- If KPIs trending down, then don’t trade the strategy until a change upwards happen, or at least trade with small size.

### Guidelines for 1-2 variables strategies
- Change variables 20-30% in step of 2-4%
- Don’t pick the best performing variable (peak)
- Look for stable region and pick a value from that region for CAGR, MAX $DD
- Keep an eye for
    - Number of trades
    - Ret/DD
    - Other important metrics

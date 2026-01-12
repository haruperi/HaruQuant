
# Building blocks

Building blocks are the fundamental components that make up entry and exit logic. Understanding each element makes it easier to construct, test, and modify strategies with intent.

### Entry blocks

Entry blocks define the conditions that must be met for a trade to trigger.

#### Common entry building blocks

1. **Indicator crossovers**
   - Moving average crossover (fast MA crosses above/below slow MA)
   - MACD line crosses the signal line
   - RSI crosses key thresholds such as 50, 30, or 70
   - Stochastic %K/%D crossover events
2. **Price pattern breakouts**
   - Breaks above/below a moving average
   - Donchian channel breakout (highest high / lowest low)
   - Support or resistance break
   - Range expansion such as Bollinger Band breakout
3. **Bar patterns**
   - Inside bars that signal consolidation
   - Outside bars that show volatility expansion
   - NR7 (narrowest range in seven bars)
   - Specific candlestick formations
4. **Threshold conditions**
   - ADX > 25 to confirm a trending market
   - Volume above an X-day average
   - ATR greater than a defined value to confirm volatility
   - Price above the 200-day MA as a trend filter
5. **Relative conditions**
   - Stock outperforming its benchmark index
   - Correlation breakdowns
   - Sector rotation or leadership signals

**Best practices**

- Keep entry logic simple, ideally one to three conditions
- Each condition must have a clear rationale
- Test conditions independently before combining them
- Avoid redundant signals (for example, MA crossover plus momentum often duplicate information)

### Entry price

Entry price determines the exact level where the order is placed once conditions fire.

#### Entry price options

1. **Market (next open/close)**
   - Enter immediately at the next available price
   - Guarantees execution in liquid markets but carries bid-ask slippage
   - Use when timing is critical and the signal is decisive
2. **Stop entry**
   - Buy stop: enter long if price rises to the trigger level
   - Sell stop: enter short if price falls to the trigger level
   - Confirms momentum before entry but risks false breakouts
   - Useful for breakout or momentum systems
3. **Limit entry**
   - Buy limit: enter long if price pulls back to the trigger level
   - Sell limit: enter short if price pushes up to the trigger level
   - Offers a better price but may miss the move entirely
   - Ideal for mean reversion, buying dips, or scale-in logic
4. **Specific levels**
   - Prior high/low plus a buffer
   - Fibonacci retracement levels
   - Pivot points
   - Round number magnets such as $100 or $50

**Offset considerations**

- Add a 1-3 tick buffer to stop entries to confirm a breakout
- Subtract 1-3 ticks from limit entries to improve fill odds
- Account for typical slippage in backtests
- Test multiple entry price styles to see which aligns with the setup

### Exit blocks

Exit blocks determine when and how positions are closed; they are as important as entries for overall expectancy.

#### Exit categories

1. **Stop loss (mandatory)**
   - Fixed dollar or point distance
   - Percentage from entry
   - ATR-based stop such as 2-5 x ATR to adapt to volatility
   - Technical stops at support/resistance or swing points
   - Time-based stops (for example, exit if not profitable within X bars)
   - Trailing stops that ratchet higher/lower as price moves favorably
2. **Profit target**
   - Fixed reward-to-risk ratios (2R, 3R, etc.)
   - ATR-based objectives (2-5 x ATR)
   - Technical levels like prior highs/lows or resistance
   - Percentage gains
   - Trailing targets that expand with the move
3. **Logic-based exit**
   - Entry signal reverses or invalidates
   - Indicator crosses back (RSI > 70 then drops below 70)
   - Moving average crossover in the opposite direction
   - Trend indicator flips
4. **Time-based exit**
   - End-of-day flatting for intraday systems
   - End-of-week exit to avoid weekend risk
   - Maximum holding period defined in bars/days
   - Exit before major scheduled news events
5. **Combination exits**
   - Scaling out: take partial profit at a target and trail the remainder
   - Multiple exit layers such as stop loss + profit target + time limit
   - Tiered targets (for example, exit one-third at each level)

**Best practices**

- Define the stop loss before entering a trade
- Test exit methods independently from entries
- Simple exit logic often outperforms overly complex rules
- Ensure exit logic is enforceable so no manual overrides are needed
- Match exit style to market context (trending versus range-bound)

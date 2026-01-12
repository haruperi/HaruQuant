
# Strategy Basic Components

Every trading strategy consists of three fundamental components: Entry logic that defines when to open a position, Exit logic that determines when to close it, and Filters that refine trade selection. Each component must be clearly defined, testable, and work together to create positive expectancy.

## Entry

Entry logic defines the conditions under which a trade is initiated. It consists of a setup (market conditions) and a trigger (specific entry level).

### Setup Logic

Setup logic identifies favorable market conditions. The setup defines WHEN to look for a trade, while the trigger defines EXACTLY when to enter.

**Common Setup Types:**
**Trend-Based:** Price above/below moving average, ADX > 25, higher highs and higher lows
**Momentum**: RSI crossing 50, MACD crossover, Rate of Change threshold
**Mean Reversion**: Price 2 standard deviations from mean, RSI &lt; 30 or &gt; 70, Bollinger Band touch
**Volatility**: ATR expanding, Bollinger Band width increasing, volatility percentile
**Pattern**: Inside bar, outside bar, multiple bar patterns, candlestick formations
**Time-Based**: Day of week, time of day, specific session, seasonal patterns

**Setup Design Principles:**
- Keep setups simple - typically 1-3 conditions maximum
- More conditions = more degrees of freedom = increased error probability = decrease in robustness.
- Each condition should have a clear logical basis
- Test setup conditions independently before combining

### Entry Level

Entry level is the specific price point where the order is placed.

**Entry Level Considerations:**
- Offset from setup bar: current close, next bar open, high/low + buffer
- Price buffer to account for spread and slippage (1-3 ticks typically)
- Order validity period: Good-till-Cancelled (GTC), Day order, specific time limit
- Consider gap risk with stop orders (may fill at much worse price)

## Exit

Exit logic determines when to close positions. Good exits are as important as good entries - they define your risk and reward profile.

### Setup Logic

Exit setup logic defines conditions that indicate the trade rationale no longer exists or profit should be taken.


**Exit Setup Categories:**
- **Adverse Price Movement:** Price against position, stop loss triggered
- **Favorable Price Movement:** Profit target reached, trailing stop triggered
- **Logic-Based:** Entry conditions reverse, indicator crosses opposite threshold
- **Time-Based:** End of day, maximum holding period, specific time reached
- **Volatility-Based:** ATR trailing stop, volatility percentile change

### Exit Level

Exit level specifies the exact price or condition for closing the position.

#### Stop Loss

Stop loss is mandatory for every strategy. It limits maximum loss per trade and prevents catastrophic losses.

**Stop Loss Methods:**
- **Fixed Dollar/Point**: Exit after $X loss or Y points/ticks. Simple but ignores market volatility.
- **Percentage**: Exit after X% loss from entry. Scales with price level.
- **ATR-Based**: 2-5 x ATR(10-20) from entry. Adjusts to market volatility. Most robust approach.
- **Technical Level**: Below support/above resistance, swing high/low, moving average. Market structure-based.
- **Time Stop**: Exit if position not profitable within X bars. Limits opportunity cost.

**Stop Loss Sizing Guidelines:**
- **Intraday strategies**: 2-3 x ATR(10) typical
- **Daily strategies**: 3-5 x ATR(20) typical
- Test various stop levels and choose stable area on performance curve
- Too tight = excessive stop-outs, too wide = large losses, no survivability benefit
- Add catastrophic stop at 2-3x normal stop for gap protection

#### Profit Target

Profit targets lock in gains at predetermined levels. They trade potentially larger wins for higher win rate and reduced risk.

**Profit Target Methods:**
- **Risk Multiple**: 1x to 5x risk (stop loss size). Simple and maintains risk-reward ratio.
- **ATR-Based**: 2-5 x ATR from entry. Scales with volatility.
- **Technical Level**: Previous high/low, Fibonacci levels, pivot points, round numbers.
- **Percentage**: Fixed % gain from entry. Common for stocks/ETFs.
- **Scaling Out**: Take partial profits at target, let remainder run with trailing stop. Balances locked profits with potential for larger wins. Example: Exit 50% at 2R, trail remaining 50% with 1 ATR stop.


#### Logic

Logic-based exits close positions when the original entry rationale no longer exists.

**Logic Exit Examples**:
- Long when RSI &gt; 50, exit when RSI &lt; 50
- Long above MA, exit when price closes below MA
- Trend following: exit when trend indicator changes direction
- Mean reversion: exit when price returns to mean

**Advantages:** Can capture large moves, adapts to market conditions, no arbitrary profit limit.
**Disadvantages:** Can give back significant open profits, requires strong discipline, may have lower win rate.

#### Indicator

Indicator-based exits use technical indicators to time the exit.

**Common Indicator Exits:**
- Parabolic SAR flip
- Moving average crossover
- MACD histogram reversal
- Stochastic crossover from overbought/oversold
- Chandelier exit (ATR-based trailing stop)

Test indicator exits independently to verify they add value. Many indicator exits reduce profitability compared to simple profit targets or stops.

#### Time

Time-based exits close positions after a predetermined period regardless of P&L.

**Time Exit Types:  **
- **End of Day (EOD)**: Close all positions before market close. Essential for intraday strategies to avoid overnight risk.
- **End of Week (EOW)**: Close before weekend. Reduces weekend gap risk.
- **Maximum Hold Period:** Exit after X bars/days. Prevents dead capital in stagnant positions.
- **Specific Time**: Exit at predetermined time (e.g., 15:45 ET). Useful for pre-close volatility avoidance.

**When to Use Time Exits:**
- Intraday strategies - EOD mandatory
- Mean reversion strategies - limit holding period
- Before major news events - avoid unpredictable volatility
- Strategies with degrading edge over time

## Filters

Filters refine when trades are taken by adding conditions that improve edge. Filters can significantly improve strategy performance but must be validated through testing.

### Volatility

Volatility filters ensure trades only occur in favorable volatility environments.

**Volatility Filter Applications:**
- **Trend Following**: Require expanding volatility (ATR increasing, Bollinger Bands widening)
- **Mean Reversion**: Require elevated volatility (ATR > X percentile, VIX spike)
- **Breakout**: Require contraction followed by expansion (squeeze pattern)

**Implementation:**
- ATR(14) > ATR(14) from 20 bars ago
- ATR percentile rank > 50th percentile (last 252 bars)
- Bollinger Band Width > X-period moving average
- VIX > 20 for equity strategies

### Direction

Direction filters align trades with larger timeframe trends or market direction.

**Direction Filter Methods:**
- Long only when daily close > 200-period MA
- Long only when weekly trend is up (higher highs and higher lows)
- Only trade in direction of index (e.g., long stocks when SPY > MA)
- Use ADX to confirm trend strength before directional trades
- Timeframe Alignment: Intraday strategy uses daily chart filter. Daily strategy uses weekly chart filter. This multi-timeframe approach often improves performance significantly.

### Pattern

Pattern filters require specific price patterns before entry.

**Common Patterns:**
- Inside bar - narrow range day after wide range
- Outside bar - engulfing previous bar's range
- NR7 - narrowest range in 7 bars
- Gap up/down - opening gap patterns
- Higher highs and higher lows sequence
- Specific candlestick patterns (hammer, doji, engulfing)

### Time

Time filters restrict trading to specific times when edge exists.

**Time Filter Examples:**
- Intraday: First hour (9:30-10:30) and last hour (15:00-16:00) only
- Day of week: Monday-Thursday only (avoid Friday uncertainty)
- Seasonal: Trade only during historically favorable months
- Avoid: FOMC days, major economic releases, holiday-shortened weeks
- Session-specific: European session (2:00-8:00 ET) or Asian session (20:00-23:00 ET)

### Additional Filter Types:

- **Volume**: Require above-average volume for breakouts, ensure liquidity
- **Correlation**: Filter based on sector or index behavior
- **Fundamental**: Earnings date proximity, sector rotation, economic indicators
- **Market Regime**: Bull/bear market, high/low VIX environment
- **Relative Strength**: Stock outperforming sector, sector outperforming market

**Filter Design Principles:**
- Each filter should improve performance measurably
- Too many filters can also lead to reduced robustness.
- Test filters independently, then in combination
- Filters should have a logical basis, not just data mining

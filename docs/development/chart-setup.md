
# Chart Setup

Strategy development is the systematic process of creating, testing, and validating trading systems. This section covers the complete workflow from initial concept to production-ready strategies, including data requirements, chart setup, building blocks, filters, ranking methods, and critical testing procedures.

Proper chart setup is the foundation of reliable strategy development. The quality of your data, timeframe selection, and session configuration directly impact backtest accuracy and live performance.

## Data

High-quality historical data is essential for accurate backtesting. Data quality issues can create false signals, misleading results, and strategies that fail in live trading.

### More is better (longer history)

Use maximum available historical data to test strategies across multiple market regimes and cycles.

**Why length matters**

- Captures different market regimes (bull, bear, sideways)
- Includes various economic cycles (expansion, recession, recovery)
- Tests strategy during high and low volatility periods
- Provides statistically significant sample size
- Reveals strategy weaknesses that only appear in specific conditions

**Recommended minimums**

- Stocks/ETFs: 15-20 years minimum (back to at least 2007-2008 crisis)
- Futures: 10-15 years minimum
- Forex: 10-15 years minimum
- Crypto: All available data (limited by market age, typically 2016+)
- Intraday strategies: Minimum 5 years, prefer 10+ years

**Critical periods to include**

- 2008-2009: Financial crisis (extreme stress test)
- 2010: Flash crash (liquidity crisis test)
- 2015-2016: Oil crash and emerging market stress
- 2018: Late-year correction
- 2020: COVID crash and recovery (fastest bear market)
- 2022: Inflation and rate hike environment

**Rule of thumb**: If your strategy was not tested through 2008-2009 and 2020, it has not been properly stress tested.

### High resolution is better (1 minute)

Use the highest resolution data available (1-minute bars minimum) even for daily strategies. Higher resolution enables better backtesting accuracy.

**Benefits of high-resolution data**

- More accurate fill simulation (intrabar movement)
- Better stop loss and profit target modeling
- Can test intraday exit rules even on daily systems
- Enables multi-timeframe analysis
- Reduces backtest overstating (bar magnifier effect)
- Allows downsampling to any timeframe without data loss

**Why not to use daily bars only**

- Daily bars assume all price levels between open and close are equally likely, which is false.
- Example scenario:
  - Daily bar: Open = $100, High = $105, Low = $95, Close = $102
  - Strategy parameters: Stop at $96 and target at $104
  - Daily view: High of $105 suggests the target filled
  - 1-minute reality: Price moved $100 → $95 → $102; the stop hit first and the target never triggered
- Result: The backtest shows a profit, but live trading shows a loss.

**Data resolution recommendations**

- Intraday strategies: 1-minute bars (tick data if available)
- Daily strategies: 1-minute bars for accurate intraday modeling
- Weekly strategies: Daily bars minimum, hourly preferred
- Futures: Tick data preferred for precision fills

Storage for 1-minute data is larger, but modern systems handle it easily and the accuracy gain is worth it.

### Futures data handling

Futures contracts expire and require special handling for continuous historical data.

#### Need continuous futures contracts for testing

Individual futures contracts expire monthly or quarterly. For backtesting, you need continuous contracts that splice multiple contract months together.

**Continuous contract construction methods**

1. **Backward ratio adjusted (recommended for most strategies)**
   - Eliminates price gaps at rollovers
   - Maintains percentage moves accurately
   - Preserves indicator calculations (RSI, MA, etc.)
   - Can show negative prices historically (not a problem)
2. **Non-adjusted (spliced)**
   - Shows actual historical prices
   - Creates gaps at rollovers
   - Can distort indicators at rollover points
   - Use only if you need actual historical price levels
3. **Forward adjusted**
   - Adjusts future prices, not past
   - Current prices match actual market
   - Distorts older data
   - Not recommended for backtesting

#### Start datasets in January 2007

Starting data from January 2007 ensures inclusion of the 2008-2009 financial crisis.

**Why January 2007 specifically**

- Captures the pre-crisis bull market (2007)
- Includes the entire 2008-2009 financial crisis
- Tests the recovery period (2009-2011)
- Provides roughly 18 years of data through 2025
- Encompasses multiple complete market cycles

#### Prioritize clean, high-quality sources

Data quality directly impacts strategy reliability. Bad data creates false signals and misleading backtests.

**Premium data providers (recommended)**

- Norgate Data: Excellent for stocks and futures, survivor-bias free
- CQG: Professional-grade futures data
- Kinetick (NinjaTrader): High-quality futures data
- IQFeed: Reliable real-time and historical data
- Trading Technologies: Institutional-grade data

**Budget options (use with caution)**

- Yahoo Finance: Free but has gaps and errors
- Alpha Vantage: Free API with rate limits
- Polygon.io: Affordable but verify quality

**Cost perspective**: Premium data costs $50-200/month, which is tiny compared to the cost of bad trades from faulty backtests. Do not save pennies to lose dollars.

### Data quality checks and validation

Always validate data before using it for strategy development. Data errors create false backtests.

**Critical checks to perform**

1. **Check for gaps and missing data**
   - Look for large time gaps between bars
   - Verify market holidays match the calendar
   - Ensure no missing trading days
   - Check for suspiciously low bar counts
2. **Validate against multiple sources**
   - Compare key price points with broker data
   - Verify major market events are reflected
   - Cross-check volume data
   - Spot-check against official exchange data
3. **Identify and handle outliers**
   - Look for impossible price spikes (bad ticks)
   - Check high/low relationships (high must be ≥ low)
   - Verify open/close are within the high/low range
   - Flag prices that deviate >20% from surrounding bars
4. **Verify corporate actions (stocks)**
   - Ensure stock splits are adjusted properly
   - Reflect dividends in adjusted prices
   - Handle merger/acquisition events correctly
   - Account for spin-offs and special dividends

**Automated validation script**

- Run automated checks before each backtest session
- Flag any data anomalies for review
- Maintain a log of issues found and corrected
- Keep a backup of original data before corrections

**Common data errors to watch for**

- Bad ticks: Single bar with extreme high/low
- Time zone errors: Bars at wrong times
- Duplicate bars: Same timestamp appears twice
- Inverted highs/lows where low price > high price
- Zero volume on active trading days
- Missing adjustments for stock splits

## Session time

Session time defines the trading hours for your strategy. Different sessions have distinct characteristics and liquidity profiles.

### Daily session

#### 9:30-16:00 ET (standard day session)

- Full regular trading hours for U.S. stocks
- Maximum liquidity and volume with all major market participants active
- Best for stock day trading and high-frequency strategies
- Use when you need maximum liquidity and tight spreads

#### 9:30-14:00 ET (shortened day session)

- Excludes the last two hours of trading
- Avoids late-day volatility spikes but misses potential closing rally/selloff
- Best for conservative intraday strategies that want to avoid unpredictable end-of-day moves

### 24-hour session

- Includes all overnight and extended hours trading
- Captures gap moves between sessions
- Comes with lower liquidity during off-hours (wider spreads and slippage)
- Suitable for forex, futures position traders, and strategies that hold overnight or react to global macro news

### Overnight session (17:00-9:30 ET example)

- Trades only during extended hours, avoiding the regular session
- Characteristics: Very low liquidity, wide bid-ask spreads, reacts to international news, sets up the next day's open, prone to gap moves
- Strategy applications: Overnight gap trading systems, pre-market reversal strategies, international news-based systems, earnings announcement plays
- Warning: Slippage and commissions erode profits quickly in overnight sessions, so only trade if you have a significant edge

#### Active sessions

Focus on the highest activity periods within the regular trading session, such as 9:00-11:00 ET.

**Morning session (9:30-11:30 ET)**

- Highest volume and volatility of the day
- Reacts to overnight news and economic releases
- Best liquidity for entries and exits
- Opening-range breakout strategies work best

**Lunch period (11:30-14:00 ET)**

- Lowest activity portion of the regular session
- Reduced volatility and choppy, directionless movement
- Best avoided for directional strategies; mean reversion may work during the lull

**Closing session (14:00-16:00 ET)**

- Volume increases into the close with end-of-day institutional flows
- Potential for trend continuation or reversal and index rebalancing effects
- Close-only strategies often capitalize on the final 15 minutes

### Special sessions

International market sessions may provide unique opportunities.

**European sessions (2:00-8:00 ET)**

- London session (3:00-11:30 ET) overlaps with the U.S. pre-market
- Highest forex volume with major European indices active
- Key economic data releases shape U.S. tone
- Excellent for EUR/USD and GBP/USD trading; can also guide ES/NQ trades

**Asian sessions (20:00-23:00 ET)**

- Tokyo session is typically the quietest major session but critical for JPY pairs
- Lower volatility overall, with the Nikkei 225 driving some futures movement
- Useful for range-bound strategies, positioning before Europe opens, and arbitrage across correlated markets

#### Custom X-minute bars

Use custom bar intervals for specialized strategy requirements (for example, 1440-minute daily bars).

**Common custom intervals**

- 1440 minutes = Daily bar (24 hours)
- 240 minutes = 4-hour bar
- 120 minutes = 2-hour bar
- 30 minutes = Half-hour bar
- 3-minute or 7-minute bars for unique edges
- Custom tick bars (for example, 1000-tick bars)

**Why use custom intervals**

- Reduce noise between standard timeframes
- Avoid over-optimization on common timeframes
- Match strategy logic to market rhythm
- Volume-based or tick-based bars normalize volatility better

Warning: Unusual timeframes may have less reliable data and more difficult execution in live trading. Test thoroughly.

## Time frame

Timeframe selection determines holding period, trade frequency, and strategy characteristics. Each timeframe has distinct advantages and challenges.

### 5-60 minute charts

**Characteristics**

- Intraday focus with 50-200+ trades per year
- Short holding periods that require active monitoring
- Higher commission costs due to frequency

**Advantages**

- No overnight risk and quick feedback on performance
- Large trade sample for statistical validation
- Ability to compound gains rapidly with multiple opportunities per day

**Disadvantages**

- Signals contain more noise and require daily attention
- Slippage and commissions add up
- Higher psychological pressure plus the need for solid technology and execution

**Best for**

- Full-time traders
- Scalping, momentum, and mean-reversion setups in liquid instruments
- Pattern-based intraday systems

### 2-8 hour bars

**Characteristics**

- Swing-trading focus with roughly 20-50 trades per year
- Holding periods of 1-5 days and less monitoring than pure intraday
- Balances noise reduction with responsiveness

**Advantages**

- Filters out much intraday noise
- More manageable for part-time traders with lower transaction costs
- Captures multi-day trends and supports multi-market portfolios

**Disadvantages**

- Overnight and weekend gap risk
- Fewer trades for statistical validation and requires patience between signals
- May miss intraday opportunities

**Best for**

- Swing traders with other commitments
- Momentum or breakout systems over 2-5 days
- Multi-market portfolio approaches

### Daily timeframe

**Characteristics**

- Swing trading with 10-40 trades per year
- Complements intraday systems and acts as a filter
- Holding periods last days to weeks with minimal monitoring (≈15 minutes per day)

**Advantages**

- Maximum noise filtering and clear end-of-day decisions
- Very low transaction costs
- Captures major trends across a diversified portfolio

**Disadvantages**

- Significant overnight risk and slower feedback cycles
- Smaller sample sizes require many years of data
- Larger stops needed, potentially missing intraday volatility

**Best for**

- Part-time traders
- Trend-following and long-term position strategies
- Diversifying alongside intraday systems or for people who cannot monitor markets live

### Weekly timeframe

**Characteristics**

- Excellent for long-term trend following and filtering daily strategies
- Very low trade frequency (5-15 trades per year) with weeks-to-months holding periods
- Often the maximum viable timeframe for retail traders

**Advantages**

- Extreme noise filtering and capture of major market moves
- Low stress, minimal monitoring, and low transaction costs
- Works well as a higher timeframe confirmation layer

**Disadvantages**

- Very small sample size that may take decades to validate
- Large drawdowns and wide stops demand significant capital
- Requires years to prove strategy effectiveness

**Best for**

- Trend following on major indices and commodities
- Higher timeframe filters for daily systems
- Long-term retirement or position trading accounts

## Signal window (EST)

Signal windows restrict when a strategy can generate entry signals, filtering trades to the most favorable intraday periods.

### Morning window (9:30-11:15 ET)

**Characteristics**

- Highest volume and volatility
- Opening range formation with institutional order flow
- Incorporates overnight news

**Best strategies**

- Opening-range breakouts
- Momentum continuation
- Gap fades and other news-driven directional trades

### Lunch window (11:15-14:30 ET)

**Characteristics**

- Lowest activity period with choppy, range-bound movement
- Reduced liquidity
- Trend continuation less reliable

**Best strategies**

- Mean reversion within the morning range
- Avoid directional or momentum systems
- Low-volatility scalping or simply waiting for the afternoon session

### Closing window (14:30-16:00 ET)

**Characteristics**

- Volume increases into the close and directional moves often resume
- Fund rebalancing flows and index futures settlement can drive price

**Best strategies**

- Trend continuation from the morning move
- Close-only systems
- Reversal setups that position for the next day, especially in the final 15 minutes

### Liquidity guardrails

Liquidity considerations are critical for execution quality and slippage management.

**Liquidity requirements**

- Target high average volume for minimal slippage
- Position size should be &lt; 1% of an average 1-minute bar's volume
- Trade during active times (for example, the first and last hour) and avoid illiquid instruments or sessions
- Test assumed slippage in a live environment

**Minimum standards**

- Stocks: Average daily volume >1 million shares
- Options: Open interest >1,000 contracts
- Futures: Average daily volume >10,000 contracts
- Forex: Stick to major pairs for smaller accounts
- Keep position size under 1-2% of average bar volume

## In-sample vs. out-of-sample

Dividing data into in-sample (IS) and out-of-sample (OOS) periods is critical for preventing overfitting and ensuring strategy robustness.

**Key principles**

- Use multiple IS/OOS periods at fixed intervals to capture all market regimes
- Default holdout period starts on January 1, 2018 for most markets
- New markets need holdouts that include multiple regimes
- Never optimize on OOS data
- Typical split is 70% IS and 30% OOS

**Why January 1, 2018**

- Captures the 2018 correction and volatility spike
- Includes the 2020 COVID crash and recovery
- Tests against recent market structure
- Provides 7+ years for OOS validation with statistical significance

**Multiple IS/OOS periods**

- Period 1: 2007-2015 (IS), 2016-2018 (OOS)
- Period 2: 2007-2017 (IS), 2018-2020 (OOS)
- Period 3: 2007-2019 (IS), 2020-2022 (OOS)
- Period 4: 2007-2021 (IS), 2022-2025 (OOS)

Strategies must perform well across all periods to be considered robust.

## Multiple timeframe setup

Using multiple timeframes can significantly improve strategy performance by filtering trades with higher timeframe context.

### Intraday with daily confirmation

- Trade intraday signals only when the daily timeframe confirms direction (for example, price above the 50-day MA)
- Example: A 15-minute bullish momentum crossover only triggers long entries when the daily trend is up
- Result: Higher win rate with fewer false signals by trading with the prevailing daily trend
- Implementation: Calculate daily indicators, apply them as filters, and consider more aggressive sizing when aligned

### Intraday with weekly confirmation

- Weekly timeframe offers a strong trend filter for intraday systems
- Use shorter lookbacks (for example, weekly MA(10) instead of MA(50)) to stay responsive
- Check the weekly trend once per week and only trade intraday signals aligned with it
- Result: Captures major multi-week moves while staying in sync with bigger-picture direction

### Daily with weekly confirmation

- Classic swing-trading setup that combines weekly trend context with daily execution
- Example: Weekly ADX > 25 and price above MA(20), while the daily chart shows a pullback to support that reverses
- Exit when the weekly trend changes or once the daily target hits

### Stock with sector confirmation

- Trade individual stocks only when their sector is strong
- Example: Trade AAPL when XLK shows positive trend and relative strength versus SPY
- Use sector leaders to anticipate sector movement, improving win rate and risk management by avoiding sector headwinds

## Direction setup

Direction setup determines whether a strategy trades long only, short only, or both directions. It can be implemented early or later as a filter.

**Options**

1. **Long only**
   - Simplest approach that benefits from the long-term equity uptrend
   - Easier to manage psychologically and avoids hard-to-borrow issues
   - Recommended default for stock trading
2. **Short only**
   - Difficult due to upward market bias and comes with unlimited theoretical loss
   - Borrow costs and availability issues persist
   - Best reserved for clear bear markets or implemented with inverse ETFs
3. **Long and short (market-neutral intent)**
   - Attempts to profit in both directions and can offset market beta
   - Provides more opportunities but is more complex
   - Requires robust short-side rules because dynamics differ from long trades

**When to use each**

- Stocks/ETFs: Long only unless you have a strong shorting edge
- Futures: Trade both directions because markets are symmetric
- Forex: Trade both directions (no inherent bias)
- Mean reversion: Frequently benefits from taking both sides

## Position sizing during development

Always begin with a fixed lot size, and only after a strategy passes robustness should you introduce risk-based sizing (1%, ATR, or volatility scaling).

**Why start with fixed lot size**

- Fixed sizing isolates the true edge by keeping expectancy, reward-to-risk, drawdown behavior, skewness, fat tails, max adverse excursion, and max favorable excursion untouched by money management
- Varying position sizes adds noise and can make a losing strategy appear profitable because compounding hides edge deterioration
- Fixed-lot backtests answer the core question: does this strategy beat randomness?

**When to add risk-based sizing (for example, 1% rule)**

- Only after the strategy shows positive expectancy, acceptable drawdowns, a smooth equity curve (efficiency ratio > 0.4, SQN > 1.6), and robustness across time periods, symbols, regimes, ATR volatility, spreads, and execution delays
- Then you can translate the edge into sensible portfolio risk

**Professional pipeline**

1. **Phase 1: Raw strategy testing (fixed lot)**
   - Use fixed lot size (0.01, 0.1, or 1), no compounding, no money management, no portfolio risk
   - Goal: Validate the core alpha
   - Metrics: Win rate, payoff ratio, expectancy, drawdown, profit factor, CAR/MDD, equity-curve R², MAE/MFE heatmaps
   - If the system fails here, nothing else matters
2. **Phase 2: Robustness testing (still fixed lot)**
   - Run walk-forward tests, Monte Carlo simulations (randomized sequence and volatility), spread/latency variations, out-of-sample sets, and time-of-day or regime splits
   - Surviving these tests indicates a real edge
3. **Phase 3: Portfolio integration (introduce risk %)**
   - Apply 1% per trade, ATR-based sizing, volatility parity, Kelly fraction, max portfolio risk exposure, and correlation-based scaling
   - Goal: Maximize return per unit of risk (Return/DD, ulcer index, etc.)
   - Only now does sophisticated risk management make sense
4. **Phase 4: Deployment scaling (dynamic)**
   - Live systems add volatility scaling, dynamic stop sizing, correlation lookbacks, portfolio heat rules, and exposure caps
   - This converts the raw edge into a scalable trading engine

**Why many retail traders fail**

- They backtest with 1% per trade, get a smooth curve, and assume the strategy is amazing
- The apparent edge is often just compounding, not robust logic, so live execution collapses

**In summary**

- Always backtest with fixed lot sizing until the strategy is validated to reveal the true edge, drawdowns, distribution, weaknesses, MAE/MFE behavior, and stability
- After that, use risk-based sizing (for example, 1% per trade, ATR sizing, volatility parity) for portfolio blending, deployment, live money management, and capital scaling

## StrategyQuant X nuances

StrategyQuant X (SQX) requires specific best practices when generating automated strategies.

**Key settings**

- Disable symmetry and test long and short separately
- Favor random generation unless the variable set is too large
- Cap entries at 1-2 conditions and use a single exit condition to preserve simplicity
- Stop loss: 2-5 ATR(10); profit target: 1-5 × stop distance
- Enforce end-of-day exits for intraday strategies and use exit end-of-range when applicable
- Optimize on net profit
- Rank a maximum of 1000 strategies so review remains manageable
- Filter out strategies that produce no trades

**Why these settings**

- Simplicity prevents overfitting
- ATR-based stops adjust to volatility
- End-of-day exits remove overnight gap risk
- Reasonable ranking sizes speed up review
- Net profit balances win rate and expectancy for practical selection

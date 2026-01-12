
## Strategy filters

Filters refine trade selection by adding conditions that improve edge. Well-designed filters can dramatically enhance strategy performance by eliminating low-probability setups and keeping the strategy aligned with the prevailing market environment.

### Index filters

Index filters ensure trades align with broader market direction. Trading with the market tide significantly improves win rate.

#### Implementation ideas

- Only take long stock signals when `SPY` sits above its 200-day moving average.
- Restrict individual stock longs to times when the related sector index is trending higher.
- Check correlation when working with high-beta names and require stronger index confirmation.
- Use `VIX` as a fear gauge and avoid new longs when `VIX > 30`.

#### Common index filters

- `SPY` (S&P 500) for broad-market equity exposure.
- `QQQ` (Nasdaq 100) for technology and growth stocks.
- `IWM` (Russell 2000) for small caps.
- Sector ETFs such as `XLF`, `XLE`, or `XLK`.
- `VIX` for volatility and fear readings.
- `USX` US Dollar index for USD currency pairs

#### Example filter logic (AAPL)

1. `SPY` above the 50-day moving average (market uptrend).
2. `XLK` above the 50-day moving average (sector strength).
3. `AAPL` outperforming `XLK` (relative strength).

Only trade when all three checks align.

#### Benefits

- Higher win rate because the market tide lifts all boats.
- Avoids fighting macro headwinds and limits catastrophic losses during crashes.
- Keeps trades on the correct side of major moves.

### Side filters

Side filters determine which direction (long or short) to trade based on the current backdrop.

#### Trend-based side selection

- Long only when price trades above the 200-day moving average.
- Short only when price remains below the 200-day moving average.
- Trade both sides when price hovers around the moving average (neutral regime).
- Use ADX to confirm trend strength before committing to a directional bias.

#### Market regime side selection

- Bull market (`SPY > 200` MA): Long only or long-biased.
- Bear market (`SPY < 200` MA): Short only or short-biased.
- Sideways market (`ADX < 20`): Trade both sides or stay flat.
- High volatility (`VIX > 30`): Reduce size or go flat entirely.

#### Seasonal side selection

- Historically bullish months favor a long bias.
- Historically bearish months favor short bias or standing aside.
- “Sell in May and go away”: reduce longs from May through October.
- Santa Claus rally: lean long during the final week of December.

#### Implementation strategy

- **Conservative**: Long only in bull markets, flat in bear markets.
- **Moderate**: Long-biased in bull, short-biased in bear, both sides in neutral regimes.
- **Aggressive**: Trade both sides year-round; adjust position sizing by regime.
- Test every variation to find the best fit for the strategy and remember that short selling carries structural challenges (upward drift, borrow costs, and theoretically unlimited risk). Most retail traders should concentrate on long-only or use inverse ETFs instead of direct shorting.

### Volume and time filters

Volume and time-based filters make sure trades trigger during optimal liquidity and volatility windows.

#### Volume filters

- **Absolute volume requirements**
  - Enforce minimum average daily volume (for example, >1M shares).
  - Demand that current volume sits above an `X`-day average to confirm participation.
  - Look for volume surges where today’s volume is more than 2× average to confirm momentum.
  - Treat declining volume during a trend as a warning.
- **Relative volume filters**
  - Require breakout volume to exceed 1.5× average.
  - Favor mean reversion when volume is below average.
  - Use volume profile to verify that liquidity exists at the entry level.
  - Compare volume to the sector or market for confirmation.

#### Time filters

- **Time of day**
  - 9:30‑10:30: Highest volatility; momentum strategies thrive.
  - 11:30‑14:00: Avoid or run only mean reversion systems.
  - 15:00‑16:00: Increased volume and trend continuation.
  - Skip 10:30‑11:00 and 14:00‑14:30 transition windows.
- **Day of week**
  - Monday: Gap patterns that often reverse the Friday close.
  - Tuesday through Thursday: Most reliable trading days.
  - Friday: Afternoon uncertainty and weekend risk.
  - Avoid half-day holiday sessions entirely.
- **Month or season**
  - January strength (January effect).
  - May through October weakness (“Sell in May”).
  - November through January strength (Santa Claus rally and year-end flows).
  - End-of-month index rebalancing can create opportunities.
- **Economic calendar avoidance**
  - FOMC announcements: extreme volatility and wide spreads.
  - Non-Farm Payrolls: first Friday of the month at 8:30 AM ET.
  - CPI and other inflation reports: market-moving prints.
  - Earnings announcements: stock-specific volatility spikes.
  - Close positions or avoid new trades 30 minutes before and after key events.

### Directional filters

Directional filters align setups with the prevailing trend using objective measurements.

- **Moving average filters**: Long only when price > 50-day MA, long only when price > 200-day MA for stricter confirmation, long when the 50-day MA crosses above the 200-day MA (golden cross), and short when those conditions reverse (death cross).
- **ADX (Average Directional Index)**: Trade only when `ADX > 25` for trending markets; rising ADX signals strengthening trends, falling ADX signals weakening trends, and `ADX < 20` suggests range-bound action better suited for mean reversion.
- **Higher highs / lower lows**: Identify uptrends by higher highs and higher lows, downtrends by lower highs and lower lows, and treat mixed signals as neutral. A 20‑50 bar lookback works well.
- **Slope or regression filters**: Calculate linear regression slope over `X` bars; positive slope favors longs, negative slope favors shorts, and steep slopes (>0.5 degrees) flag powerful trends.
- **Multi-timeframe trend alignment**: Confirm that higher timeframes agree with the trading timeframe (for example, daily uptrend plus 15-minute uptrend). Avoid or downsize trades when timeframes conflict.

**Implementation tips**

- Test multiple directional filters to find the best combination.
- Combine two or three complementary filters (for example, MA + ADX + slope) for higher conviction.
- Lean heavily on directional filters in trending markets and disable or invert them in range-bound regimes.

### Volatility filters

Volatility filters make sure each strategy trades in the environments it was designed for.

#### Volatility measurement tools

- **ATR (Average True Range)**: ATR(14) is standard; rising ATR signals expanding volatility that favors breakouts, while falling ATR suggests mean reversion. Compare ATR to its 20-day average or convert it into a percentile rank.
- **Bollinger Bands**: Band width equals `(Upper Band - Lower Band) / Middle Band`. Narrow bands highlight contraction and potential squeezes; wide bands flag high volatility and possible consolidation.
- **Historical volatility**: Calculate the standard deviation of returns over 20‑30 days. High HV means large price swings and wider stops, while low HV supports tighter stops. Compare against implied volatility to spot discrepancies.
- **VIX (volatility index)**: `VIX < 15` indicates complacency, `15-25` is normal, `25-35` is elevated fear, and `>35` is extreme fear that may warrant reduced exposure.

#### Strategy-specific volatility filters

- **Trend following**: Require expanding volatility (ATR rising, ATR above its moving average, Bollinger Bands widening) and note that trends often strengthen when VIX rises.
- **Mean reversion**: Prefer elevated volatility (ATR spikes, VIX > 20) and price excursions beyond 2‑3 standard deviations; avoid low volatility environments.
- **Breakouts**: Look for contraction followed by expansion such as ATR at the low end of its yearly range or a Bollinger Band squeeze (narrowest width in `X` bars) and then wait for expansion to confirm the breakout.

#### Practical implementation

- Calculate ATR percentile rank over the past 252 bars (≈1 year).
- Treat &lt;25th percentile as low volatility, 25th‑75th percentile as normal, and >75th percentile as high.
- Adjust strategy selection and position sizing to match the detected volatility bucket.

### Pattern filters

Pattern filters identify price formations that precede high-probability moves.

- **Inside bar**: Current bar fully contained within the previous bar, signaling consolidation and upcoming breakouts (multiple inside bars amplify the coil).
- **Outside bar / engulfing bar**: Current bar engulfs the prior range, indicating volatility expansion and possible reversal; bullish when a large up bar follows a down bar, bearish in the opposite case.
- **NR7**: Narrowest range in seven bars, pointing to extreme consolidation and imminent expansion; trade the breakout in the direction of the prevailing trend.
- **Gap patterns**: Gap up, gap down, exhaustion gaps (reversal signals), breakaway gaps (trend continuation), and gap fills for mean reversion.
- **Candlestick patterns**: Hammer or hanging man, doji, morning/evening star formations, three white soldiers, and three black crows.
- **Chart patterns**: Triangles, head and shoulders, double tops/bottoms, flags or pennants, and cup and handle structures.

**Pattern implementation**

- Automate pattern recognition with objective rules and test each pattern independently before combining it with other logic.
- Combine patterns with volume and trend confirmation and treat them as additional filters rather than primary entry signals.
- Most traditional chart patterns have weak statistical edge on their own, so use them sparingly.

### Seasonality filters

Seasonal patterns exploit recurring calendar-based tendencies in markets.

#### Types of seasonal patterns

- **Monthly seasonality**: January effect (small caps outperform), “Sell in May and go away,” Santa Claus rally (last five trading days of December plus first two of January), September weakness, and November through January strength.
- **Intra-month patterns**: Turn-of-month effect (last day plus first four days strongest), mid-month weakness (days 10‑20), window dressing (month-end fund rebalancing), and options expiration on the third Friday (heightened volatility).
- **Day of week patterns**: Monday gaps that often reverse Friday, Tuesday through Thursday consistency, Friday afternoon weakness, and pre-holiday bullish bias.
- **Intraday patterns**: Opening 30 minutes (highest volatility and volume), 10:30‑11:00 reversals, lunch doldrums (11:30‑14:00), 15:00‑16:00 volume surges, and last 15 minutes of institutional rebalancing.
- **Commodity seasonality**: Crude oil strength in summer (driving season) and winter (heating), natural gas peaks in winter and summer, grains tied to planting/harvest cycles, heating oil strength from October through March, and gasoline strength from April through August.
- **Holiday effects**: Pre-holiday bullish bias, post-holiday continuation or reversal, and reduced-liquidity holiday-shortened weeks (avoid half days).

#### Implementation guidelines

- Test seasonal patterns with at least 10 years of data and remember that seasonal edges are small; they work best as filters or bias, not standalone signals.
- Combine seasonality with technical confirmation, monitor structural market changes, and log which seasonal tendencies continue to work.

#### Research sources

- *Stock Trader’s Almanac* for definitive seasonal references.
- Seasonax.com for commodity seasonality data.
- Your own research; test every claim independently before implementation.

### Higher timeframe filters

Higher timeframe (HTF) filters align trades with the bigger picture, improving win rates and reducing whipsaws.

#### Why higher timeframe filtering works

- Filters out noise from the trading timeframe.
- Keeps trades aligned with the dominant trend and reduces false signals.
- Improves risk-reward by catching larger moves and bolsters trader confidence.

#### Common higher timeframe relationships

- Intraday (5‑15 minute) systems filtered by the daily or weekly chart.
- Daily systems filtered by the weekly chart.
- Weekly systems filtered by the monthly chart.
- General rule: the higher timeframe should be 4‑6× the trading timeframe.

#### Higher timeframe filter methods

- **Simple trend filter**: Require the HTF price to sit above/below a moving average (for example, daily chart above the 50-day MA for 15-minute longs) and only trade in that direction.
- **Multi-MA alignment**: Look for HTF alignment such as 20-MA > 50-MA > 200-MA to confirm strong uptrends (inverse for downtrends).
- **HTF momentum confirmation**: Require HTF RSI > 50, HTF MACD above zero, or HTF ADX > 25 to couple trend and momentum strength.
- **HTF structure**: Confirm the HTF is making higher highs and higher lows, is not immediately at resistance, and still has room before overbought/oversold extremes.

#### Implementation example

- For a 15-minute system, check the daily chart once per day. If the daily closes above the 20-day MA, maintain a long bias; if it sits below, favor shorts or stand aside. Take 15-minute signals only in the allowed direction. Expect fewer trades, higher win rate, larger average wins, better Sharpe, and shallower drawdowns.
- Critical rule: never trade against the higher timeframe trend unless the system is explicitly counter-trend.

### Market regime filters

Market regime filters adapt strategy behavior to the current environment because different regimes favor different approaches.

#### Major market regimes

- **Trending vs. range-bound**: Trending markets feature `ADX > 25` and respect moving averages; range-bound markets have `ADX < 20` and oscillate around the mean. Trend strategies favor the former, mean reversion favors the latter.
- **High vs. low volatility**: High volatility occurs when `VIX > 25` with wide ranges; low volatility occurs when `VIX < 15` with tight ranges. High volatility favors mean reversion and wider stops; low volatility favors breakout prep and tighter stops.
- **Bull vs. bear vs. sideways**: Bull markets show `SPY > 200-day MA` with higher highs, bear markets show `SPY < 200-day MA` with lower lows, and sideways markets oscillate around the long-term average. Match strategy direction accordingly.
- **Risk-on vs. risk-off**: Risk-on regimes display low VIX, strong commodities, and investor appetite for equities, while risk-off regimes show high VIX, flows into bonds, USD strength, or gold bids.

#### Regime detection methods

- **ADX-based**: `ADX > 25` indicates trending, `ADX < 20` indicates range-bound, and 20‑25 is a transition zone.
- **Volatility percentile**: Calculate ATR or VIX percentile rank over 252 days; &gt; 75th percentile is high volatility, &lt;25th is low, and middle values are normal.
- **Moving-average slope**: Measure the 50-day MA slope over 20 bars; steep slopes confirm trends, flat slopes signal ranges, and changing slopes warn of regime shifts.
- **Correlation analysis**: High cross-market correlation indicates risk-off (everything moving together), while low correlation reflects healthier risk-on dispersion.

#### Adaptive strategy selection

- Enable trend-following systems and disable mean reversion in trending regimes; flip the logic in range-bound regimes.
- Reduce position sizes and widen stops during high volatility; revert to normal sizing and prepare for breakouts in low volatility.
- During regime transitions, reduce overall exposure until conditions clarify.

#### Implementation

- Calculate the regime daily (before the open), adjust strategy parameters or switch systems accordingly, avoid intraday regime changes, keep a regime-change log, and test multiple definitions to find the best fit.

### Alternative data filters

Alternative data offers edges beyond price and volume, but it must be tested rigorously.

#### Types of alternative data

- **Sentiment data**: Put/call ratio, CNN Fear & Greed Index, AAII sentiment survey, social media sentiment (Twitter, Reddit, StockTwits), news sentiment analysis, and VIX-based fear gauges.
- **Positioning data**: COT reports, short interest, institutional ownership changes, insider buying/selling, and large options flow.
- **Economic indicators**: ISM PMI, consumer confidence, yield-curve spreads (10Y‑2Y), unemployment trends, housing starts, and credit spreads.
- **Intermarket relationships**: Dollar strength, bond yields, gold prices, crude oil, and sector rotation cues.
- **Breadth indicators**: Advance-decline line, new highs vs. new lows, percentage of stocks above the 50-day or 200-day moving average, and sector leadership.

#### Using alternative data effectively

- **As filters**: Sentiment extremes (&gt;80% bullish or &lt;20% bullish) flag reversals, high short interest plus bullish technicals hint at squeezes, breadth divergence warns of market tops, and inverted yield curves suggest reducing risk.
- **As confirmation**: Match technical breakouts with positive sentiment, combine insider buying with oversold setups, and marry sector outperformance with stock breakouts.
- **As early warning**: Widening credit spreads signal risk reduction, deteriorating breadth points to potential tops, VIX spikes justify hedges, and yield-curve inversions warn about recessions 6‑18 months out.

#### Data sources and caution

- FRED for free economic data, Quandl for alternative datasets, Barchart.com for COT data, and mainstream sources such as MarketWatch, Yahoo Finance, or broker research portals for sentiment and positioning.
- Alternative data can be lagging, noisy, or unreliable. Always backtest before relying on it, because many popular indicators have weak statistical edge.

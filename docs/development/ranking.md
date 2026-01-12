
## Ranking

After generating multiple strategy candidates, ranking helps identify the most promising systems for further development and eventual deployment.

### Fitness function (net profit)

The fitness function determines how strategies are scored and prioritized. Net profit is the recommended primary metric because it:

- Provides a clear, unambiguous objective focused on real dollars.
- Balances win rate, average win/loss, and trade frequency implicitly.
- Avoids arbitrary weighting across multiple metrics.
- Stays simple to explain to stakeholders.

#### Alternative fitness functions

1. **Sharpe ratio**
   - Pros: Compares risk-adjusted returns across strategies.
   - Cons: Favors low-volatility, low-return systems; best used as a secondary filter.
2. **Profit factor**
   - Pros: Measures efficiency via gross profit divided by gross loss.
   - Cons: Ignores trade frequency and capital usage; compare only within similar systems.
3. **Return / max drawdown**
   - Pros: Balances return with risk of ruin and suits conservative mandates.
   - Cons: Max drawdown can reflect a single outlier event.
4. **Custom scoring**
   - Pros: Lets you weight multiple preferences (for example, 40% net profit, 30% Sharpe, 30% win rate).
   - Cons: Adds complexity and introduces arbitrary weights that are harder to optimize.

**Recommendation:** Optimize primarily for net profit, then layer additional filters such as minimum Sharpe (>0.5), minimum trades (>30), or minimum average trade (> $100) to maintain quality.

### In-sample expectations

The in-sample (IS) period is where optimization occurs. Good IS results are required but never sufficient on their own.

**IS goals**

- Produce strategies with positive expectancy and logical construction.
- Keep trade counts high enough (100+ trades, 200+ preferred) to avoid statistical noise.
- Avoid excessive curve fitting by limiting condition count and parameter tweaks.

**Target metrics**

- Net profit: Meaningful for the instrument class (for example, &gt;$50k on futures).
- Profit factor: &gt;1.5 minimum, &gt;2.0 preferred.
- Sharpe ratio: &gt;0.8 minimum, &gt;1.2 preferred.
- Win rate: 45‑70% depending on style.
- Average trade: &gt;$100 after costs.
- Max drawdown: &lt;30% of net profit.

**Red flags**

- Win rate above 85% or a near-perfect equity curve.
- Profit factor above 5.0.
- Very few losing trades or &lt;50 trades over a decade.
- Extremely complex logic (more than five stacked conditions).

**Best practices**

- Embrace “good enough” IS results; perfection never survives OOS.
- Favor simple, intuitive logic blocks.
- Require performance consistency across individual years, especially in the most recent two to three.

### Out-of-sample validation

Out-of-sample (OOS) testing proves the strategy was not tailored to historical noise.

**OOS requirements**

- Reserve at least 20‑30% of the dataset (30‑40% preferred) that is never touched during optimization.
- Cover different regimes and include recent years (2018‑2025).
- Ensure the period contains at least one meaningful market event.

**Performance expectations**

- 70‑90% of IS net profit is acceptable.
- Sharpe, win rate, and profit factor should stay within 20‑30% of IS values.
- The equity curve should retain the same general shape without catastrophic drawdowns (>50% of capital).

**Examples**

- *Healthy degradation*: IS net $100k / Sharpe 1.2 / win rate 58% versus OOS net $75k / Sharpe 1.0 / win rate 54%.
- *Problematic*: IS net $80k / Sharpe 1.5 / win rate 62% versus OOS net $40k / Sharpe 0.8 / win rate 45%.

**Warning signs**

- OOS profit falls below 50% of IS or becomes negative while IS was strong.
- Sharpe collapses from &gt;1.5 to &lt;0.5.
- Win rate plunges more than 15 percentage points.
- Long stretches without trades or an equity curve that looks unrelated to IS.

**If OOS fails**

- Discard the strategy regardless of IS results.
- Analyze the failure (overly complex logic, regime mismatch, etc.) to inform future development.
- Never re-optimize on failed OOS data—doing so simply creates a new IS period.

### Full-sample review

A full-sample review combines IS and OOS periods to ensure the strategy works across the complete history.

**Why it matters**

- Reveals behavior across every regime.
- Highlights recent degradation or periods of extreme underperformance.
- Provides the most realistic expectations going into production.

**Analysis checklist**

1. **Year-by-year breakdown**: Aim for profitable results in 70‑80% of years, with recent years staying positive.
2. **Equity curve shape**: Look for a steadily rising curve where drawdowns recover quickly and flat spots are limited.
3. **Regime consistency**: Validate performance in bull markets (2009‑2020), corrections (2011, 2015, 2018, 2020), and sideways periods. Strategies should succeed in at least two of the three.
4. **Metric stability**: Win rate, average trade, frequency, and profit factor should stay within roughly ±10‑20% of their long-term values.

**Red flags**

- Profits concentrated in only one or two banner years.
- Recent years losing money while legacy periods were strong.
- Max drawdowns exceeding 40% of account equity.
- Trade frequency or win rate steadily declining.

**Acceptable full-sample metrics**

- Net profit: Positive and material for your account size.
- Profit factor: &gt;1.5.
- Sharpe ratio: &gt;0.7.
- Win rate: 40‑70% based on strategy style.
- Maximum drawdown: &lt;30% of total net profit.
- Winning years: &gt;70% overall, with the past three years profitable.

### Eliminate similar strategies

After ranking, remove redundant strategies so the portfolio reflects true diversification instead of duplicated exposure.

**Why de-duplication matters**

- Two nearly identical strategies behave like one oversized position.
- Correlated systems fail simultaneously, creating a false sense of diversification.
- Portfolio optimizers assume some independence between return streams.

**Similarity detection methods**

1. **Correlation of returns**:
   - &gt;0.7: Too similar—keep the stronger one.
   - 0.5‑0.7: Moderately similar—evaluate before keeping both.
   - &lt;0.5: Acceptably different; negative correlation is ideal.
2. **Logic comparison**: Review entry and exit rules to see whether one strategy is just a minor variation of another.
3. **Trade overlap**:
   - &gt;80% overlap: Essentially the same strategy.
   - 50‑80% overlap: Moderately similar.
   - &lt;50% overlap: Distinct enough.
4. **Equity curve similarity**: Overlay equity curves; if they track closely, treat them as duplicates.

**Decision framework**

- Favor the strategy with better OOS performance.
- If OOS is similar, pick the simpler logic.
- If still tied, choose the one with higher Sharpe or stronger recent profitability.
- Discard the rest.

**Portfolio construction targets**

- Average pairwise correlation below 0.3.
- No strategy pair above 0.7 correlation.
- Blend styles (trend following, mean reversion, breakout), timeframes (intraday, daily, weekly), and instruments (equities, futures, forex) to spread risk.

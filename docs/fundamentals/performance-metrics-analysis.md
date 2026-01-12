
# Performance Metrics Analysis

Proper performance evaluation requires multiple metrics. No single metric tells the complete story. Understanding these metrics helps identify strategy strengths and weaknesses.

## Return Metrics

Absolute return measures without considering risk.

- **Net Profit**: Total profit after all costs. Most basic measure. Doesn't account for capital employed or time
- **Total Return %**: Net profit / Starting capital x 100. Better than absolute profit - shows efficiency of capital use
- **CAGR**: Compound Annual Growth Rate. Normalizes returns across different time periods.
Formula: (Ending Value / Starting Value)^(1/Years) - 1. Example: Turn $10k into $20k in 3 years = 26% CAGR
- **Average Trade Return**: Total profit / Number of trades. Shows average edge per trade

## Risk-Adjusted Metrics

Account for risk taken to achieve returns. More important than absolute returns.

- **Sharpe Ratio**: (Return - Risk-Free Rate) / Standard Deviation. Measures return per unit of volatility. Higher is better. >1.0 = good, >2.0 = excellent (target), >3.0 = outstanding. Limitations: Treats upside and downside volatility equally
- **Sortino Ratio**: Like Sharpe but uses downside deviation only. Better metric - penalizes only harmful volatility. Generally 20-40% higher than Sharpe for same strategy
- **Calmar Ratio**: CAGR / Maximum Drawdown. Shows return relative to worst loss. >0.5 = good, >1.0 = excellent. Conservative metric favored by hedge funds.
Example: Strategy A: 50% return, 40% drawdown, Calmar = 1.25. Strategy B: 30% return, 15% drawdown, Calmar = 2.0. Strategy B is superior despite lower absolute return.

## Drawdown Metrics

Measure peak-to-trough declines. Critical for psychological and financial survival

- **Maximum Drawdown (MDD)**: Largest peak-to-trough decline. Most important risk metric. Your account must survive MDD x 1.5 to continue trading. Example: 30% MDD means you need capital buffer to survive 45%+ loss
- **Average Drawdown**: Mean of all drawdown periods. More representative of typical experience than MDD
Recovery Factor: Net Profit / MDD. How many times you earn back the worst loss. >3.0 = good, >5.0 = excellent, >10.0 = exceptional
- **Time to Recovery**: Days to return to peak after drawdown. Psychological killer if too long. >6 months tests discipline

**Reality Check**: Live trading often experiences 1.5-2x backtest MDD. If backtest shows 25% MDD, expect 35-50% in live trading. Plan accordingly.

## Trade Statistics

Granular metrics about trade outcomes.

- **Win Rate**: % of profitable trades. Winning trades / Total trades x 100. Not predictive of profitability alone. 30%-win rate can be profitable with good R:R
- **Profit Factor**: Gross Profit / Gross Loss. How many dollars won per dollar lost.
&lt; 1.0 Losing system - more losses than profits
1.0 - 1.3 Marginally profitable — barely worth trading
1.3 – 1.5 Moderate edge — some promise but may be fragile
1.5 - 2.0 Solid system — commonly targeted by professionals
&gt; 2.0 Excellent strategy — strong edge, but maybe hard to sustain long term
- **Average Win / Average Loss**: Reward-to-risk ratio. &gt; 1.5:1 = good, &gt;2:1 = excellent. Can be profitable with &lt;1:1 if the win rate is high enough
- **Expectancy**: (Win Rate × Avg Win) - (Loss Rate × Avg Loss). Average profit per trade. Must be positive. Higher = better. Accounts for both win rate and R:R
- **Largest Win / Loss**: Identifies outliers. If best trade = 50% of profit, strategy too dependent on rare winners

**Trade Count Requirements:**
- Minimum 30 trades for basic confidence
- 100+ trades for reliable statistics
- 300+ trades for high confidence
- Fewer trades = larger random variance in results


## Statistical Significance
Determine if results are due to edge or luck.

- T-Statistic: Measures how many standard deviations returns are from zero. T &gt; 1.96 = statistically significant at 95% confidence. T &gt; 2.58 = 99% confidence
- P-Value: Probability results due to chance. P &lt; 0.05 = significant (5% chance of luck). P &lt; 0.01 = highly significant
- Confidence Intervals: Range where true result likely lies. 95% CI: [Lower, Upper]. If CI includes zero, results not significant

**Sample Size Impact:**
- Small samples: Large confidence intervals, unreliable
- Large samples: Narrow intervals, reliable
- Never trust strategy with &lt; 30 trades

## Benchmark Comparison
Compare strategy performance to passive alternatives.

- Buy-and-Hold: Compare to simply buying and holding the instrument. Your strategy must beat this or it's not worth the effort. Include dividends in comparison
- Index Comparison: ES strategies vs SPY buy-hold. Forex strategies vs currency ETF. Must outperform on risk-adjusted basis
- Alpha: Excess return above benchmark adjusted for risk. Positive alpha = outperformance
- Beta: Correlation to benchmark. Beta = 1 means move with market. Beta &lt; 1 = less volatile. Beta &gt; 1 = more volatile. Low beta desirable for diversification

**Critical Question:** "Why not just buy the index?" Your strategy must have compelling answer: Higher returns, Lower drawdowns, Better risk-adjusted returns, or Uncorrelated returns (diversification benefit).

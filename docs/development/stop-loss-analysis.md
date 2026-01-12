
## Stop loss analysis

Stop loss placement directly determines expectancy. Stops that are too tight cause churn, while stops that are too wide allow catastrophic losses. Use the following process to dial in robust levels.

### Step 1 — Add commission and slippage

- Include realistic costs before optimizing: stocks $1‑5 per trade, futures $4‑10 round trip, forex 1‑3 pips plus 1‑3 ticks of slippage.
- Without costs, the optimizer gravitates toward fragile parameters that never survive live trading.

### Step 2 — Plot stop size versus profit

- Build a scatter plot with stop size on the X-axis and net profit on the Y-axis.
- Sweep a wide range (for example, 1‑10 ATR in 0.25‑0.5 ATR increments) to understand the response curve.
- Avoid relying on edge values; they usually represent local optima.

### Step 3 — Identify the stable area

- Look for plateaus where multiple stop values produce similar profit (e.g., 2.5‑4.0 ATR).
- Choose the midpoint of the stable range to maximize robustness instead of chasing the single best datapoint.

### Step 4 — Add a catastrophic stop

- Layer a disaster stop at roughly 2‑3× the optimized stop (optimized 3 ATR ⇒ catastrophic 9 ATR).
- This stop should trigger on only 1‑2% of trades but protects against gaps, news shocks, and account blowups.
- Cap maximum loss per position at 5‑10% of account equity.

### Step 5 — Retest with final stops

- Re-run backtests using both the working stop and the catastrophic stop.
- Confirm profitability, reasonable stop-hit frequency (commonly 30‑60%), and acceptable drawdowns.
- If performance collapses with realistic stops, discard the strategy.

### Step 6 — Inspect KPI impact

- Profit factor should remain >1.5, Sharpe near the original target, win rate within a normal band, and max drawdown within tolerance.
- Review recovery time from the largest drawdown; if it balloons, your stops are likely still misaligned.

### Stop loss sizing guidelines

- Mean reversion: 1.5‑3 ATR (quick exits).
- Breakout: 2‑4 ATR (room for initial pullbacks).
- Trend following: 3‑6 ATR (handle volatility).
- Scalping: 0.5‑2 ATR (tight by design).
- Position trading: 5‑10 ATR (long holding periods).

### Common mistakes

- Stops placed too tight or too wide.
- Fixed-dollar stops that ignore volatility.
- Operating without catastrophe protection.
- Moving stops against yourself and turning winners into losers.
- Failing to test a range of stop sizes systematically.

### Always use hard stops

“Mental” stops inevitably fail during fast markets or emotional decision points. Publish actual stop orders so the platform enforces discipline even when you hesitate.

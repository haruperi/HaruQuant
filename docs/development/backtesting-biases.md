
## Backtesting biases & pitfalls

Backtests only matter when they mirror live-trading reality. The following biases routinely inflate paper performance and must be neutralized before funding a strategy.

### Look-ahead bias

**Definition:** Using information that was unavailable at the decision point (for example, using the close to trigger an entry at the same close, or assuming you know whether a stop or target hit first).
**Common sources:** Indicators calculated on incomplete bars, daily bars that “guess” intrabar sequences, and unrealistic order-fill assumptions.
**Mitigations:**
- Use only completed bars and add a one-bar delay if necessary.
- Employ bar magnification (1-minute data for daily systems).
- Model fills conservatively and add slippage.
- Compare backtests to walk-forward or paper-trade results—large discrepancies signal bias.

### Survivorship bias

**Definition:** Testing only on instruments that still exist today (survivors) while excluding delisted or bankrupt names.
**Impact:** Inflates returns by 1‑5% annually, especially on small-cap equity universes.
**Mitigations:**
- Use survivorship-bias-free data (Norgate, CRSP) that includes delisted tickers.
- Focus on indices/futures where the instrument itself survives.
- Account for bankruptcy risk via wider stops, diversification, and haircutting results by 1‑3% if you cannot obtain bias-free data.

### Data-snooping bias

**Definition:** Testing so many variations that some appear profitable purely by chance. Automated strategy generators or aggressive parameter sweeps exacerbate the issue.
**Mitigations:**
- Always reserve 30‑40% of data for OOS testing; discard strategies that fail OOS.
- Use walk-forward analysis with rolling IS/OOS windows.
- Run Monte Carlo reshuffles to ensure results fall within expected ranges.
- Limit logic complexity and insist on intuitive explanations—if you cannot articulate the edge, it is likely noise.
**Reality check:** Even with a solid process, expect 70‑90% of candidates to fail OOS; only 5‑20% of promising backtests typically survive to live trading.

### Curve fitting / overfitting

**Definition:** Tailoring a strategy too closely to historical noise so it collapses in the future.
**Warning signs:** Extremely high IS metrics (Sharpe >3, win rate >90%), highly complex logic (>5 conditions), sharp drop in OOS performance, and hypersensitivity to small parameter changes.
**Mitigations:** Limit parameters (ideally 1‑3), demand 100+ trades, require OOS and walk-forward confirmation, and test parameter stability (neighboring settings should perform similarly). If you cannot explain the logic succinctly, assume it is overfit.

### Unrealistic slippage and commissions

**Problem:** Ignoring transaction costs turns marginal systems into supposed winners.
**Baseline assumptions:**
- Futures (ES): $5 per round trip commission + 2 ticks ($25) slippage ≈ $30 total.
- Stocks (intraday): $4 commissions + ~$4 slippage per round trip.
- Forex (EUR/USD): 2-pip round-trip cost ≈ $20 per lot.
**Rule:** Average trade profit must exceed at least 3× total costs; otherwise the edge is too thin.

### Transaction cost analysis

Factor every cost component:

1. **Bid-ask spread:** Paid on every market order; larger for illiquid names.
2. **Market impact:** Your order moves price—keep size below 1‑2% of average bar volume.
3. **Opportunity cost:** Limit orders may never fill; assume 30‑50% miss rate in tests.
4. **Exchange and regulatory fees:** SEC, ORF, clearing fees, etc.

**Testing protocol:** Evaluate the strategy at 0%, 50%, 100%, and 150% of estimated costs. Reject anything that fails at 100% costs, and strongly prefer systems that remain profitable at 150% for safety. Higher-frequency systems must devote even more edge to overcoming costs, so prioritize liquidity, limit orders when feasible, and negotiate lower commissions.

By proactively managing these biases, your reported performance will better match forward tests, and you will avoid funding strategies built on statistical mirages.

# Edge Lab: Symbol-Specific Edge Discovery Toolkit

Edge Lab is a framework for discovering and statistically validating trading edges **before** committing to production strategies. It applies the scientific method to trading: hypothesis, experiment, statistical validation.

## Quick Start

```bash
# Demo mode (no MT5 required)
python scripts/run_edge.py --symbol EURUSD --timeframe M15 --eds all --demo

# With real MT5 data
python scripts/run_edge.py --symbol EURUSD --timeframe M15 --eds all

# Multi-symbol screening
python scripts/run_edge.py --symbols EURUSD,GBPUSD,USDJPY --timeframe H1 --eds mr
```

## What You Get

- **EDS-0**: Null Models / Baseline (establish what random trading produces)
- **EDS-1**: Mean Reversion Detector (compression + z-score fade)
- **EDS-2**: Trend Persistence Detector (high-ATR breakout follow-through)
- **EDS-3**: Session Edge Detector (time-of-day alpha)
- Block bootstrap confidence intervals (autocorrelation-aware)
- R-space permutation tests
- Multiple hypothesis correction (Benjamini-Hochberg FDR)
- Markdown + JSON reporting

## Philosophy

Traditional strategy development often leads to curve-fitting:
1. Backtest with many parameters
2. Pick the best result
3. Wonder why it fails in live trading

Edge Lab flips this approach:
1. **Hypothesize**: State a clear market behavior hypothesis
2. **Test**: Run a minimal rule-based strategy
3. **Validate**: Use rigorous statistics to prove/disprove
4. **Compare to Null**: Ensure results beat random chance

---

## Edge Discovery Strategies (EDS)

### EDS-0: Null Models / Baseline

**Purpose**: Establish what "no edge" looks like before claiming one exists.

Baselines computed:
- Random-entry, fixed-exit (same holding period distribution)
- R-space simulation (preserving ATR-based stop distances)
- Shuffled returns (break temporal structure)

**Your strategy must beat the 95th percentile of null results.**

```bash
python scripts/run_edge.py --symbol EURUSD --eds null
```

### EDS-1: Mean Reversion Detector

**Hypothesis**: In low-volatility (compressed) regimes, extreme z-score deviations revert to the mean.

**Entry Conditions**:
- Bollinger Band Width in bottom quartile (compression)
- Z-score beyond threshold (e.g., |z| > 2.0)

**Exit**: Mean touch (z crosses 0) or time stop

**Configuration**:
```python
from apps.edge import MeanReversionConfig

cfg = MeanReversionConfig(
    sma_n=20,
    z_entry=2.0,
    bbw_n=20,
    compression_q=0.25,
    max_hold_bars=32,
    k_stop_atr=1.2,
)
```

### EDS-2: Trend Persistence Detector

**Hypothesis**: After breakout in high-volatility regimes, momentum persists.

**Entry Conditions**:
- ATR in top 30% (high volatility)
- Price breaks N-bar high/low

**Exit**: Target (k×ATR), time stop, or opposite breakout

**Why It Works**: High-ATR regimes often signal institutional participation.

### EDS-3: Session Edge Detector

**Hypothesis**: Price behavior differs by trading session (Asia/London/NY).

**Strategies Tested**:
- Session opening range breakout
- Session mean-reversion fade

**Statistical Guard**: Benjamini-Hochberg FDR correction for multiple testing.

---

## Statistical Methods

### Block Bootstrap CI

Standard bootstrap assumes IID samples, but trade returns have autocorrelation. Block bootstrap preserves this structure.

```python
from apps.edge import block_bootstrap_ci
ci_low, ci_high = block_bootstrap_ci(
    r_multiples,
    statistic=np.mean,
    n_boot=2000,
    block_size=20,
    ci_level=0.95,
)
```

### R-Space Null Distribution

Simulate random entries in R-multiple space (normalized by stop distance):

```python
from apps.edge import r_space_null, permutation_test
null_dist = r_space_null(
    df, n_trades=200, hold_bars=32,
    side="BUY", k_stop_atr=1.5, atr_series=atr,
)
pval = permutation_test(observed_exp, null_dist)
```

### Multiple Hypothesis Correction

```python
from apps.edge import benjamini_hochberg
significant = benjamini_hochberg(p_values, q=0.10)
```

---

## Acceptance Criteria

An edge is **confirmed** when:
1. Bootstrap CI lower bound > 0
2. Permutation p-value < 0.05
3. Sample size >= 200 trades
4. Results exceed 95th percentile of null baseline

| Verdict | Meaning |
|---------|---------|
| EDGE_CONFIRMED | CI > 0 AND p < 0.05 - Strong evidence |
| POTENTIAL_EDGE | CI > 0 but p >= 0.05 - Investigate further |
| WEAK_SIGNAL | Positive expectancy but CI includes 0 |
| NO_EDGE | Negative expectancy |
| INSUFFICIENT_DATA | < 30 trades - Need more data |

---

## Programmatic Usage

```python
from apps.edge import (
    EdgeLabConfig,
    DataConfig,
    load_ohlc,
    run_eds_mean_reversion,
    run_eds_null_baseline,
    print_result_summary,
)
from apps.mt5.client import MT5Client

# Configure
cfg = EdgeLabConfig(
    data=DataConfig(symbol="EURUSD", timeframe="M15", end_pos=5000),
)

# Load data
client = MT5Client()
df = load_ohlc(client, "EURUSD", "M15", 0, 5000)

# Establish baseline first
null_result = run_eds_null_baseline(df, "EURUSD", "M15", cfg.null, cfg.bootstrap, cfg.perm)

# Run strategy
result = run_eds_mean_reversion(df, "EURUSD", "M15", cfg.mr, cfg.bootstrap, cfg.perm)

# Print verdict
print_result_summary(result)

# Check if edge confirmed
if result.stats.ci_low > 0 and result.stats.p_value_perm < 0.05:
    print("Edge statistically confirmed!")
```

---

## Output Structure

Results are saved to `edge_lab_outputs/`:

```
edge_lab_outputs/
├── EURUSD_M15_EDS0_null.md
├── EURUSD_M15_EDS0_null.json
├── EURUSD_M15_EDS1_meanreversion.md
├── EURUSD_M15_EDS1_meanreversion.json
├── EURUSD_M15_EDS2_trendpersistence.md
├── EURUSD_M15_EDS2_trendpersistence.json
├── EURUSD_M15_EDS3_session.md
├── EURUSD_M15_EDS3_session.json
└── summary.md
```

---

## Module Structure

```
apps/edge/
├── __init__.py          # Public API exports
├── config.py            # Configuration dataclasses
├── datasets.py          # Data loading, session tagging
├── features.py          # Technical indicators (40+)
├── null_models.py       # Statistical tests
├── eds_null_models.py   # EDS-0: Baseline detector
├── eds_mean_reversion.py # EDS-1: Mean reversion
├── eds_trend_persistence.py # EDS-2: Trend following
├── eds_session.py       # EDS-3: Session edge
├── reporting.py         # Markdown/JSON output
├── results_schema.py    # Result dataclasses
└── README.md            # This file
```

---

## Best Practices

1. **Start with EDS-0**: Always establish null baseline first
2. **Sufficient Data**: Use 3000+ bars minimum, 5000+ preferred
3. **Don't Cherry-Pick**: Run full analysis, not just favorable periods
4. **Multiple Timeframes**: Test hypothesis across M15, H1, H4
5. **Out-of-Sample**: Reserve 30% of data for validation
6. **Document Everything**: Save reports for audit trail

---

## Integration with RiskGovernor

Once an EDS produces a proven edge, convert it to production:

1. Define precise entry/exit rules
2. Set stop_distance (ATR-based)
3. Add slippage assumptions

Then RiskGovernor handles:
- Portfolio VaR/ES
- Risk contribution caps
- Correlation risk
- Margin management

**Strategy focuses on edge. Risk system focuses on survivability.**

---

## Examples

See `scripts/examples/edge_discovery_example.py` for comprehensive examples:

1. Basic edge discovery for single symbol
2. Multi-symbol screening
3. Session analysis
4. Custom parameters
5. Null baseline comparison
6. Exploratory data analysis

---

## References

- Van Tharp: *Definitive Guide to Position Sizing*
- Efron & Tibshirani: *An Introduction to the Bootstrap*
- Lopez de Prado: *Advances in Financial Machine Learning*
- Bailey et al.: *The Probability of Backtest Overfitting*

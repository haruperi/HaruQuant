# Robustness Test Matrix & Scorecard Integration

This document formalizes the **robustness-testing workflow** into a **stage-gated matrix** with:

* correct execution order
* explicit purpose per test
* numeric pass / kill thresholds
* clear classification (HARD / SOFT / DIAGNOSTIC)
* direct integration into the **Strategy Scorecard**

The objective is to reliably filter **symbol-specific trading strategies** from a large candidate pool down to **1 live-ready strategy per symbol**, while minimizing curve‑fit risk.

---

## 0. Classification Legend

| Label           | Meaning                                 |
| --------------- | --------------------------------------- |
| **HARD FILTER** | Failure ⇒ immediate rejection           |
| **SOFT FILTER** | Failure ⇒ heavy score penalty / review  |
| **DIAGNOSTIC**  | Informational only (no rejection)       |

---

## 1. Robustness Test Matrix (Correct Order)

### Stage 0 — Development (Candidate Generation)

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| 0 | **Initial Generation & In-Sample Filtering** | Generate pool of candidate strategies | GEN | Edge (Base), Risk, Simple | PF ≥ 1.5, Ret/DD ≥ 0.5 p/a, Trades ≥ 2000 | Strategy Name; Symbol (IS); TimeFrame (IS); # of trades; Profit factor; Annual % Return; Ret/DD Ratio; Drawdown; Stability; Symmetry; Stagnation; Winning Percent |

---

### Stage A — Temporal Generalization (Edge Existence)

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| A1 | **Second OOS Test (Pre‑Development Period)** | Proves edge existed *before discovery* (10Mins) | HARD | Edge (100% of pillar foundation) | OOS PF ≥ 1.3 **AND** Ret/DD ≥ 0.5 p/a | Strategy Name; Symbol (IS); TimeFrame (IS); # of trades; Profit factor; Annual % Return; Ret/DD Ratio; Drawdown; Stability; Symmetry; Stagnation; Winning Percent |
| A2 | **Third OOS Test (Post‑Development Period)** | Proxy for future performance | HARD | Edge + Stability (100% of pillar foundation) | OOS PF ≥ 1.3 **AND** annualized return ≥ 70% of IS **AND** DD ≤ 1.3× IS DD | Strategy Name; Symbol (IS); TimeFrame (IS); # of trades; Profit factor; Annual % Return; Ret/DD Ratio; Drawdown; Stability; Symmetry; Stagnation; Winning Percent |

> Rationale: If an edge does not survive *both sides* of the dev window, it is almost certainly overfit.

---

### Stage B — Execution Realism (Live Survivability)

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| B1 | **Spread Stress Test (95–99% percentile)** | Realistic spread widening | HARD | Robustness (10% of pillar) | PF drop ≤ 30% **AND** Ret/DD ≥ 70% of baseline | Strategy Name; Symbol (IS); # of trades; Profit factor; Ret/DD Ratio; Drawdown; Commission/Swap (); Stability |
| B2 | **Spread Stress Test (Max ever)** | Flash‑event sensitivity | DIAGNOSTIC | Robustness (Diagnostic) | No hard rule (observe collapse behavior) | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Drawdown (diagnostic) |
| B3 | **Slippage Test (fixed + volatility‑scaled)** | Entry/exit realism | HARD | Robustness (10% of pillar) | PF ≥ 1.00 **AND** Ret/DD ≥ 0.50× baseline | Strategy Name; Symbol (IS); # of trades; Profit factor; Ret/DD Ratio; Drawdown; Commission/Swap () |
| B4 | **Execution Delay (±1 bar entry & exit)** | Latency & requote proxy | HARD | Robustness (10% of pillar) | Net Profit > 0 **AND** PF ≥ 1.00 | Strategy Name; Symbol (IS); # of trades; Profit factor; Net profit; Ret/DD Ratio; Drawdown |

---

### Stage C — Statistical Robustness (Distribution Integrity)

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| C1 | **MC Randomize Trades Order (Exact)** | Sequence dependence | HARD | Robustness (35% of pillar) | 95% MC runs profitable **AND** Ret/DD(95%) ≥ 50% baseline | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Drawdown; ZScore; ZProbability (if MC export lacks survival) |
| C2 | **MC Randomize Trades Order (Resampling)** | Over‑reliance on rare trades | HARD | Robustness (15% of pillar) | 95% MC runs profitable **AND** DD inflation ≤ 1.5× | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Drawdown; ZScore; ZProbability |
| C3 | **MC Randomly Skip Trades (10%)** | Missed fills / broker rejects | HARD | Hard Filter Only | PF ≥ 1.00 **AND** Ret/DD ≥ 0.50× baseline | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Drawdown; Winning Percent |
| C4 | **MC Randomize Parameters (±10–20%)** | Curve‑fit detection | SOFT | Fragility (60% of penalty) | ≥ 70% perturbed runs profitable | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Stability; Avg. Parameters Stability; Worst Parameters Stability |
| C5 | **MC Randomize History Data** | Microstructure fragility | SOFT | Fragility (40% of penalty) | PF degradation ≤ 40% | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Stability; StandardDev |
| C6 | **MC Overall (All Combined)** | Extreme stress | HARD (Late) | Robustness (20% of pillar) | 95% MC equity > 0 **AND** Ret/DD ≥ 0.40× baseline | Strategy Name; Symbol (IS); Profit factor; Ret/DD Ratio; Drawdown; ZScore; ZProbability |
| C7 | **MAE/MFE Edge Efficiency Test** | Stability of edge capture | DIAGNOSTIC | Stability (Diagnostic) | Edge ratio > 1.0 (Positive expectancy) | Strategy Name; Symbol (IS); Biggest MAE; Total MFE; Avg. Win; Avg. Loss; Win/Loss ratio (or export MAE/MFE report) |

---

### Stage D — Structural Generalization (Optional / Intent‑Driven)

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| D1 | **Another Market Test** | Universality of idea | DIAGNOSTIC | N/A | No rejection unless multi‑symbol intent | Strategy Name; Symbol; TimeFrame; Profit factor; Ret/DD Ratio; Annual % Return; Drawdown |
| D2 | **Different Timeframe Test** | Time alignment fragility | DIAGNOSTIC | N/A | Informational only | Strategy Name; Symbol; TimeFrame; Profit factor; Ret/DD Ratio; Annual % Return; Drawdown |

---

### Stage E — Adaptability vs Stability

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| E1 | **WFM (Fixed Parameters)** | True edge validation | HARD | Hard Filter Only | PF ≥ 1.05 **AND** Ret/DD ≥ 0.30 | Strategy Name; Symbol; # of trades; Profit factor; Annual % Return; Ret/DD Ratio; Drawdown; Stability; Stagnation |
| E2 | **WFO (Rolling Optimization)** | Adaptability check | DIAGNOSTIC | Diagnostic | Used for comparison only | Strategy Name; Symbol; Profit factor; Ret/DD Ratio; Annual % Return (diagnostic) |
| E3 | **WFM‑on‑WFO Results** | Anti‑curve‑fit validation | HARD | Hard Filter Only | Performance degradation ≤ 30% | Strategy Name; Symbol; Profit factor; Ret/DD Ratio; Drawdown; Stability |

---

### Stage F — Final Reporting

| Order | Test | Purpose | Type | Score Target | Pass / Kill Rule | SQX exports |
| ----- | ---- | ------- | ---- | ------------ | ---------------- | ----------- |
| F1 | **Final Test (Whole Period)** | Sanity & visualization | DIAGNOSTIC | N/A | Never used for rejection | Strategy Name; Symbol; Profit factor; Annual % Return; Ret/DD Ratio; Drawdown (diagnostic only) |

---

## 2. Integration into Strategy Scorecard

### Scorecard Pillars & Weights

| Pillar                         | Weight | Tests Feeding It             |
| ------------------------------ | ------ | ---------------------------- |
| **Edge Quality**               | 30%    | A1, A2, E1                   |
| **Robustness**                 | 30%    | B1–B4, C1–C6, E3             |
| **Stability & Consistency**    | 20%    | A2, C2, C3                   |
| **Risk & Capital Efficiency**  | 15%    | DD inflation, Ret/DD ratios  |
| **Simplicity & Deployability** | 5%     | Parameter count, sensitivity |

---

### Mapping Tests → Score Contributions

| Test Group                 | Score Impact                |
| -------------------------- | --------------------------- |
| Pre & Post OOS             | +EdgeScore +StabilityScore  |
| Spread / Slippage / Delay  | +RobustnessScore            |
| MC Exact / Resample / Skip | +RobustnessScore            |
| MC Param / History         | −Fragility penalty          |
| WFM / WFM‑on‑WFO           | +EdgeScore +RobustnessScore |

Failures in **HARD FILTERS** force **FINAL SCORE = 0** (rejected).

SOFT failures apply linear penalties (e.g. −5 to −15 points).

---

## 3. Final Selection Rule (Per Symbol)

When ≤3 strategies remain for a symbol:

1. Must pass **all HARD FILTERS**
2. Rank by **FINAL SCORE (0–100)**
3. If scores within **±2 points**:

   * choose higher MC survival
   * choose lower parameter count
   * choose smoother equity (lower PF variance)

---

## 4. Core Principle (Non‑Negotiable)

> **Robustness is not the absence of failure under extreme stress.
> Robustness is controlled degradation under stress.**

This matrix enforces that principle quantitatively.

---

**Document version:** 1.0
**Intended use:** StrategyQuant X + external Python scoring pipeline

---

# Appendix A: Scorecard Specification (v1)

This section defines the **Python-ready, reproducible scoring specification** to compute a single composite score **FINAL_SCORE (0–100)** for each strategy.

## 1) Data Model

### 1.1 Entities

**StrategyRow**: one record per `strategy_name`. `stage` tracks the latest stage seen (e.g., `core`, `oos2`, `wfm`).

### 1.2 Keys

| Field         | Type | Notes                                          |
| ------------- | ---: | ---------------------------------------------- |
| `symbol`      |  str | e.g. `EURUSD`                                  |
| `strategy_name` |  str | SQX strategy name (unique)                   |
| `variant_id`  |  str | optional; use if multiple parameter sets exist |
| `stage`       |  str | stage label as above                           |
| `asof_date`   | date | export timestamp                               |

---

## 2) SQX Export Column Schema

### 2.1 Required Base Metrics (per stage)

| Column                   |  Type | Meaning                                                                           |
| ------------------------ | ----: | --------------------------------------------------------------------------------- |
| `net_profit`             | float | net profit in account currency                                                    |
| `gross_profit`           | float | gross profit                                                                      |
| `gross_loss`             | float | gross loss (negative or abs; standardize to positive magnitude)                   |
| `profit_factor`          | float | PF                                                                                |
| `max_drawdown_pct`       | float | max DD in % (0–100)                                                               |
| `return_pct`             | float | total return %                                                                    |
| `annual_return_pct`      | float | annualized return %                                                               |
| `ret_dd`                 | float | Return / Drawdown (use return_pct / max_drawdown_pct)                             |
| `trades`                 |   int | number of trades                                                                  |
| `avg_trade`              | float | average trade profit                                                              |
| `median_trade`           | float | median trade profit                                                               |
| `win_rate`               | float | 0–1                                                                               |
| `avg_win`                | float | average winning trade                                                             |
| `avg_loss`               | float | average losing trade magnitude (positive)                                         |
| `max_consecutive_losses` |   int | max consecutive losing trades                                                     |
| `stagnation_days`        | float | max stagnation in days                                                            |
| `time_in_market_pct`     | float | 0–100 (if available; else optional)                                               |

### 2.2 Required OOS/IS Split Summary (for development stage)

| Column                         |  Type | Meaning                                                |
| ------------------------------ | ----: | ------------------------------------------------------ |
| `is_profit_factor`             | float | IS PF                                                  |
| `oos_profit_factor`            | float | OOS PF                                                 |
| `is_ret_dd`                    | float | IS Ret/DD                                              |
| `oos_ret_dd`                   | float | OOS Ret/DD                                             |
| `is_annual_return_pct`         | float | IS annual return %                                     |
| `oos_annual_return_pct`        | float | OOS annual return %                                    |
| `oos_profitable_windows_ratio` | float | 0–1 = (# profitable OOS windows) / (total OOS windows) |
| `pf_degradation_ratio`         | float | `oos_profit_factor / is_profit_factor`                 |
| `retdd_degradation_ratio`      | float | `oos_ret_dd / is_ret_dd`                               |

### 2.3 Required Stress / MC Outputs (per stress suite)

| Column                          |  Type | Meaning                                                  |
| ------------------------------- | ----: | -------------------------------------------------------- |
| `mc_survival_rate`              | float | 0–1 = fraction of simulations profitable (or equity > 0) |
| `mc_retdd_p95_ratio`            | float | Ret/DD at 95% confidence divided by baseline Ret/DD      |
| `mc_dd_inflation`               | float | p95 DD / baseline DD                                     |
| `slip_pf_ratio`                 | float | PF under slippage / baseline PF                          |
| `slip_retdd_ratio`              | float | Ret/DD under slippage / baseline Ret/DD                  |
| `spread_p99_retdd_ratio`        | float | Ret/DD under p99 spread / baseline Ret/DD                |
| `delay_pf_ratio`                | float | PF under delay / baseline PF                             |
| `param_perturb_profitable_rate` | float | 0–1 = fraction profitable under ±10–20% params           |
| `history_perturb_pf_ratio`      | float | PF under history perturb / baseline PF                   |
| `mc_overall_retdd_ratio`        | float | Ret/DD under combined MC / baseline Ret/DD               |
| `mc_overall_survival_rate`      | float | 0–1 combined MC survival                                 |

### 2.4 Optional Deployability Columns

| Column            | Type | Meaning                                  |
| ----------------- | ---: | ---------------------------------------- |
| `indicator_count` |  int | count indicators                         |
| `parameter_count` |  int | tunable parameters                       |
| `mtf_count`       |  int | number of TFs used (e.g. 3 for M1/M5/H1) |

---

## 3) Normalization Functions (Exact)

All subscores are computed on **0–1**, then scaled to 0–100 at the end.

### 3.1 Clamp
`clamp(x, lo, hi) = min(max(x, lo), hi)`

### 3.2 Min–Max Normalization (monotonic)
```
# larger is better
norm_up(x, lo, hi) = clamp((x - lo) / (hi - lo), 0, 1)

# smaller is better
norm_down(x, lo, hi) = clamp((hi - x) / (hi - lo), 0, 1)
```

### 3.3 Logistic Normalization (soft saturation)
`logistic(x, mid, steep) = 1 / (1 + exp(-steep * (x - mid)))`
* PF: `mid=1.20`, `steep=4.0`
* Ret/DD: `mid=0.80`, `steep=3.0`

### 3.4 Ratio Normalization
`ratio_score(r) = norm_up(r, 0.50, 1.10)`

---

## 4) Stage-Gate Filters (Hard Failures)

If any HARD filter fails at the applicable stage, set: `REJECTED = True`, `FINAL_SCORE = 0`

### 4.1 Universal Minimums

| Rule                          | Threshold                        |
| ----------------------------- | -------------------------------- |
| Trades (final decision stage) | `trades >= 300` (10y M1 systems) |
| Profit Factor (OOS3/final)    | `profit_factor >= 1.00`          |
| Net Profit (critical stages)  | `net_profit > 0`                 |
| Max DD                        | `max_drawdown_pct <= 40`         |

### 4.2 Robustness Matrix Hard Filters (encoded)
`HARD_PASS = all(pass_* columns required for your decision gate)`

---

## 5) Pillar Subscores (0–1)

### 5.1 Edge Quality (30%)
Inputs: `oos_profit_factor`, `oos_ret_dd`, `oos_annual_return_pct`, `oos_profitable_windows_ratio`
* `pf_s = logistic(oos_profit_factor, mid=1.20, steep=4.0)`
* `retdd_s = logistic(oos_ret_dd, mid=0.80, steep=3.0)`
* `ann_s = norm_up(oos_annual_return_pct, lo=0, hi=40)`
* `winwin_s = clamp(oos_profitable_windows_ratio, 0, 1)`

```
EDGE = 0.40*pf_s + 0.35*retdd_s + 0.15*ann_s + 0.10*winwin_s
```

### 5.2 Robustness (30%)
Inputs: `spread_p99_retdd_ratio`, `slip_retdd_ratio`, `delay_pf_ratio`, `mc_survival_rate`, `mc_retdd_p95_ratio`, `mc_dd_inflation`, `mc_overall_survival_rate`, `mc_overall_retdd_ratio`

* `spread_s = ratio_score(spread_p99_retdd_ratio)`
* `slip_s = ratio_score(slip_retdd_ratio)`
* `delay_s = ratio_score(delay_pf_ratio)`
* `mc_surv_s = clamp(mc_survival_rate, 0, 1)`
* `mc_retdd_s = ratio_score(mc_retdd_p95_ratio)`
* `dd_infl_s = norm_down(mc_dd_inflation, lo=1.0, hi=1.5)`
* `mc_all_surv_s = clamp(mc_overall_survival_rate, 0, 1)`
* `mc_all_retdd_s = ratio_score(mc_overall_retdd_ratio)`

```
ROBUST = (
  0.10*spread_s +
  0.10*slip_s +
  0.10*delay_s +
  0.20*mc_surv_s +
  0.15*mc_retdd_s +
  0.15*dd_infl_s +
  0.10*mc_all_surv_s +
  0.10*mc_all_retdd_s
)
```

### 5.3 Stability & Consistency (20%)
Inputs: `max_consecutive_losses`, `stagnation_days`, `pf_degradation_ratio`

* `stagn_s = norm_down(stagnation_days, lo=0, hi=30)`
* `consec_s = norm_down(max_consecutive_losses, lo=4, hi=12)`
* `deg_pf_s = ratio_score(pf_degradation_ratio)`

```
STABILITY = 0.40*deg_pf_s + 0.30*stagn_s + 0.30*consec_s
```

### 5.4 Risk & Capital Efficiency (15%)
Inputs: `ret_dd`, `max_drawdown_pct`, `time_in_market_pct`

* `retdd_s = logistic(ret_dd, mid=0.80, steep=3.0)`
* `dd_s = norm_down(max_drawdown_pct, lo=10, hi=40)`
* `tim_s = norm_down(time_in_market_pct, lo=20, hi=80)`

```
RISK = 0.55*retdd_s + 0.35*dd_s + 0.10*tim_s
```

### 5.5 Simplicity & Deployability (5%)
Inputs: `parameter_count`, `indicator_count`, `mtf_count`

* `par_s = norm_down(parameter_count, lo=5, hi=25)`
* `ind_s = norm_down(indicator_count, lo=2, hi=12)`
* `mtf_s = norm_down(mtf_count, lo=1, hi=4)`

```
SIMPLE = 0.45*par_s + 0.45*ind_s + 0.10*mtf_s
```
If deployability columns missing, set `SIMPLE = 0.5`.

---

## 6) Soft Penalties (Applied After Pillars)

### 6.1 Fragility Penalty (0–1)
Inputs: `param_perturb_profitable_rate`, `history_perturb_pf_ratio`

* `pp_s = norm_up(param_perturb_profitable_rate, lo=0.70, hi=0.95)`
* `hist_s = ratio_score(history_perturb_pf_ratio)`

```
FRAGILITY_PENALTY = 0.10 * (1 - (0.60*pp_s + 0.40*hist_s))
```

---

## 7) FINAL_SCORE (Reproducible)

### 7.1 Pillar Weighting
```
BASE = (
  0.30*EDGE +
  0.30*ROBUST +
  0.20*STABILITY +
  0.15*RISK +
  0.05*SIMPLE
)
```

### 7.2 Convert to 0–100 and apply penalties
`FINAL_SCORE = 100 * clamp(BASE - FRAGILITY_PENALTY, 0, 1)`

### 7.3 Rejection Override
If `REJECTED`: `FINAL_SCORE = 0`

---

## 8) Tie-Break Rules (Per Symbol)

If finalists within **±2 points**:
1. higher `mc_overall_survival_rate`
2. higher `mc_overall_retdd_ratio`
3. lower `parameter_count`
4. lower `max_drawdown_pct`

# THE THIRD OOS TEST

This test is easy. We can run the backtest using the last data sample because the strategy has passed all previous test.

### General Guidelines

- For all type of strategies, start from 2010 till 2019, as it contains multiple market regimes for most instruments. Leave 2020 till 2024 for robustness testing.
- When testing for robustness then include all data 2010-current date (exclude last year - 2025)
- For Seasonal/Bias intraday strategies, and manual simple strategies with manual robustness, include all data 2010-current date (exclude last year).
- Last excluded year should contain > 25 trades to derive dependable metrics readings.
- Once strategy passes robustness testing go through last year of data and compare to strategy metrics. This is the final verdict, it should behave the same way.

### Ranking Filters

- OOS number of trades > 25
- OOS Profit Factor > 1
- OOS Return/Drawdown Ratio > 1
- OOS Annualized % Return / IS Annualized % Return > 70%

## Robustness Testing Checklist

### 1. Manual Guidelines & Overview
- [ ] **Data Usage**: Use all data, leave Hold Out Period covering same market regimes.
- [ ] **Lookback**: Prefer longer lookback periods for stability.
- [ ] **Filters**: Don't layer too many; each must add significant improvement.
- [ ] **Risk**: Fixed SL/TP (2-4 ATR). SL should be for protection, not strategy enhancement.
- [ ] **Optimization**: Do not optimize Strategy Filters, SL, or TP if using WFM/SPP.

### 2. Core Validation
- [ ] **Selection**: Copy strategies from Builder (don't move).
- [ ] **Data Settings**: Precision 1 min tick, full data range (pre-builder period).
- [ ] **Cross Checks**: Uncheck "Retest with higher precision".
- [ ] **Ranking Filtering**:
    - [ ] Profit Factor (IS) > 1.3
    - [ ] Ret/DD Ratio (IS) > 0.5 per year
    - [ ] Delete FAILED strategies.

### 3. Stress Tests
#### Trades Cost Test
- [ ] **Commission & Swap**: Set to Current/Max.
- [ ] **Spread**: Set to Max Value.
- [ ] **Slippage**: 5 pips (Forex) / 20 (Gold) or Max Value.
- [ ] **Ranking**: PF (IS) > 1.1, Ret/DD (IS) > 0.5.

#### Monte Carlo Simulations (200 sims, 95% Confidence)
- [ ] **Randomise Trades (Exact)**: Ret/DD > 50% of original.
- [ ] **Randomise Trades (Resampling)**: Ret/DD > 25% of original.
- [ ] **Randomly Skip Trades (10%)**: Ret/DD > 50% of original.
- [ ] **Randomise Strategy Params (20% prob, 30% max change)**: Ret/DD > 50% of original.
- [ ] **Randomise History Data (30% prob, 10% ATR max change)**: Ret/DD > 50% of original.
- [ ] **Randomise Slippage (0-5) & Spread (0-5)**: Ret/DD > 50% of original.
- [ ] **MC Overall**: Combine all above (History 10%, Slippage 0-5, Spread 1-5).

#### Portfolio & Risk
- [ ] **Correlation**: Filter similar strategies (Ret/DD), check monthly correlation.
- [ ] **Risk Tolerance**: 10% per pair.
- [ ] **Post-Test (OOS2)**: Verify validity on post-builder data (PF > 1.1, Ret/DD > 0.3).

### 4. Parameter Discovery & Optimization
- [ ] **3D Charts**: Test parameter pairs (SL/TP, etc.) for stability.
- [ ] **Simple Optimization**: Test recommended parameters.
- [ ] **Success Criteria (All Strategies)**:
    - [ ] % Profitable run > 60%
    - [ ] % Avg Profit > 0, Distribution < 0
    - [ ] % Annual % Return >= SPP Return
    - [ ] % CAGR < SPP CAGR
- [ ] **Execution**: Run System Parameter Permutation.

### 5. Final Test (Third OOS)
- [ ] **Data**: Run backtest on last data sample (2020-2024/Current).
- [ ] **Ranking Filters**:
    - [ ] OOS Trades > 25
    - [ ] OOS Profit Factor > 1
    - [ ] OOS Return/Drawdown > 1
    - [ ] OOS Annual % Return / IS Annual % Return > 70%

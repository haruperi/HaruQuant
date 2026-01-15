# Core Validation

If we had one strategy we would go to parameter optimization first, but since we have many strategies generated, we want to first do simple filtering tests to eliminate weak strategies so that we can only do time consuming optimizations on the best strategies only.

### From the builder select all strategies from the Builder section
- Copy strategies not move
- Load /Copy current settings to use the same settings used in build

![Builder Selection](/img/core-validation-1.png)

### Data Settings
- **In Data -> Test Parameters -> Precision** (set: 1 minute data tick simulation)
- **In Data -> Backtest Data Settings -> Start day / End day** (set: Time period pre the period used in builder)
- **In Data -> Data range parts** -> reset, have all data in sample

![Data Settings](/img/core-validation-2.png)

### Cross Checks
- **In Cross Checks (Robustness)** -> (uncheck: Retest with higher precision)

### Ranking
- **In Ranking -> Strategy Filtering conditions** -> (set: Profit Factor (IS) > 1.3, Ret/DD Ratio (IS) > 0.5 per year, multiply with # of years , check: Delete FAILED strategies from Databank)

![Ranking Settings](/img/core-validation-3.png)

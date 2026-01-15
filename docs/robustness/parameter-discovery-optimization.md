# Parameter Discovery & Optimization

This phase is about finding the best settings for your strategy on a set historical data (in-sample data).

### Test using 3D charts

**A few important points**
- We find out which parameters of the strategy are working
- We test parameter pairs
    - Stop loss and take profit
    - Strategy parameter pairs
    - etc.

**Move strategies to Optimiser by saving to the computer and reloading in the Optimiser.**

**Go to Strategy Config and Apply Strategy Config**

**Go to Optimizations and select Simple Optimization**

**On Parameter Optimizations select what you want to optimize and just make sure Total combinations are not too big.**

![Optimization Settings](/img/param-optimazition-1.png)

### General guidelines

- SPP follows the same logic, where it will optimize the strategy and find a stable area for most important metrics. It does that by getting a median value for all metrics which is assumed to be the realistic estimation of future performance, and if the strategy is within 1 StDev of the median then it is robust.
- Same problem with WFO & WFA exist here, which is there isn’t enough permutations or too many permutations to chose from.
- The original paper suggested to do Monte Carlo testing on generated curves. But that is still estimate nested in SQX
- Standard deviation testing from the mean is still not implemented.

### Success Criteria

- **All Strategy**
    - % Profitable run > 60%
    - % Avg Profit > 0, Distribution < 0
    - % Annual % Return >= Annual % Return (SPP)
    - % CAGR < CAGR (SPP)

- **EA Strategy**
    - % Profitable run > 70%
    - % Avg Profit > 0, Distribution < 0
    - % Annual % Return >= 150% Annual % Return (SPP)
    - % CAGR < 125% CAGR (SPP)

### Cross check - Opt. Profile / Sys. Param. Permutation

This cross check performs optimization of the strategy and then evaluates its Optimization profile - see the conditions in filter.

![Cross Check Settings 1](/img/param-optimazition-2.png)

![Cross Check Settings 2](/img/param-optimazition-3.png)

1.  **Optimization Report:** The very first step. You run your strategy with a range of different inputs (e.g., moving average length) to find the most profitable combination on your test data.
2.  **System Parameters Permutation:** A more exhaustive form of optimization where you test all possible combinations of your system's parameters to see how they interact.
3.  **Test using 3D charts:** This is not a test but a visualization tool used during optimization. It helps you see how two different parameters affect the strategy's performance, making it easier to spot stable parameter areas.

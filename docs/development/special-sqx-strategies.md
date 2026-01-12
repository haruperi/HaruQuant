
## Special SQX strategies

StrategyQuant X (SQX) offers powerful automation, but raw brute force creates noisy outputs. Combine randomization with clear constraints to generate a manageable, higher-quality candidate pool.

### Advanced SQX techniques

1. **Randomization with constraints**
   - Allow SQX to randomize, but limit the building-block pool to proven indicators.
   - Exclude redundant components (multiple similar MAs, overlapping oscillators) to speed generation and reduce junk strategies.
2. **Template-based generation**
   - Predefine structures such as “MA crossover + momentum confirmation” for trend following or mean reversion.
   - Let SQX optimize parameters inside your structure so domain expertise guides the search.
3. **Multi-market strategy search**
   - Generate candidates that must work across multiple symbols to filter for universal patterns instead of instrument quirks.
   - Expect fewer passing strategies, but those that do are more robust.
4. **Asymmetric long/short rules**
   - Build separate logic for longs versus shorts. Longs often thrive on trend rules, while shorts may prefer mean reversion or exhaustion signals.
5. **Filter after generation**
   - Keep generation broad, then apply aggressive post-processing filters (minimum trades, OOS thresholds, max complexity).
   - Automatically eliminate similar strategies to avoid duplicate logic.

### Recommended SQX workflow

1. Define the objective up front (timeframe, market, style).
2. Configure reasonable building-block constraints before running the engine.
3. Generate 1,000‑5,000 candidates to ensure a statistically meaningful pool.
4. Rank by in-sample net profit.
5. Filter for quality: OOS profit >50% of IS, minimum trades, acceptable complexity.
6. Remove highly correlated strategies (return correlation >0.7).
7. Manually review the top 20‑50 systems for logic sanity.
8. Run walk-forward analysis on the top 10.
9. Paper trade the best 3‑5 before allocating real capital.

This process balances the power of automated strategy creation with human oversight, ensuring only robust SQX outputs progress to testing and funding.

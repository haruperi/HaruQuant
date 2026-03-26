• Overview

  The Edge Lab system is now a full research pipeline that starts with raw OHLCVS data, turns it into an analysis-ready dataset, runs multiple
  structure and edge engines on top of that dataset, persists the results, and then validates whether those conclusions actually matched later
  market behavior.

  The main flow is:

1. Load and prepare one shared dataset on /edge-lab
2. Reuse that same prepared dataset across all Edge Lab tabs
3. Run analysis engines like Core Metric, Discovery, and Market Structure
4. Persist runs and normalized outputs
5. Validate saved Market Structure conclusions against later realized price behavior
6. Calibrate and stress-test the model through profile calibration, stability, and robustness

  The main backend entrypoints live around:

- apps/edge/datasets.py
- apps/edge/market_structure.py
- apps/api/routes/edge.py
- apps/sqlite/edge_discovery.py

  ———

1. Data Foundation

  Everything begins with the analysis-ready OHLCVS pipeline. The system does not let each tab fetch and interpret raw broker data independently
  anymore. Instead, Edge Lab has one shared dataset-first workflow.

  The landing page /edge-lab is now the Data tab. It:

- fetches raw OHLCVS
- validates schema and logic
- cleans the data
- enriches it
- stores the prepared dataset in session memory so other tabs reuse it without re-downloading

  Core backend pieces:

- apps/edge/data/validation.py
- apps/edge/data/cleaning.py
- apps/edge/data/enrichment.py
- apps/edge/data/models.py

  What that pipeline guarantees:

- canonical OHLCVS schema
- logical OHLC checks
- timestamp continuity checks
- duplicate detection
- spread and volume validation
- missing-bar handling
- weekend / holiday handling
- spread anomaly handling
- enrichment fields like:
  - returns
  - log returns
  - pip/point metadata
  - body/range/wick pips
  - session/time features
  - rollover-hour flags

  This shared dataset is exposed to the UI through the Edge Lab session context:

- ui/src/contexts/edge-lab-data-context.tsx

  That means Discovery, Core Metric, Seasonality, and Market Structure all operate on the same prepared data snapshot.

  ———

2. Core Metric Layer

  The Core Metric tab is the first descriptive layer on top of the prepared dataset. It gives a basic symbol profile with:

- returns metrics
- ROC metrics
- candle anatomy
- range metrics
- volatility
- spread
- basic volume/activity

  This engine lives under:

- apps/edge/core_metrics

  It uses the shared finance math rather than an isolated Edge metrics file. Earlier duplication was removed so Edge-specific metrics are no longer
  fragmented across separate files.

  Outputs are persisted in normalized form via the SQLite edge manager and surfaced in the Core Metric tab UI. The Core Metric page can also save,
  load, and delete runs.

  ———

3. Discovery Layer

  The Discovery tab still runs the EDS workflows, but it now uses the same prepared dataset model instead of owning its own data-fetch form.

  This means the old Edge Discovery workflows now sit properly inside the dataset-first architecture:

- load once on Data
- analyze many times elsewhere

  The Discovery UI still supports saved runs, viewing details, and deletion.

  ———

4. Market Structure Engine

  This is now the main structural intelligence layer of Edge Lab.

  User-facing route:

- /edge-lab/market-structure

  Core engine:

- apps/edge/market_structure.py

  This engine answers:

- is the symbol trend-biased?
- reversion-biased?
- mixed?
- how trustworthy is that conclusion?
- what kind of strategy fits it?
- how tradeable is that structure after friction considerations?

### 4.1 Swing and Structure Logic

  The engine starts by detecting swings from the prepared dataset:

- pivot-based local swing highs/lows
- optional ATR threshold filtering
- ambiguous same-bar high/low swing cases are skipped

  From swings it labels:

- HH
- HL
- LH
- LL

  Then it builds directional chains and legs:

- chain lengths
- follow-through behavior
- broken trends
- leg amplitudes in pips
- leg duration in bars
- pullback depth/duration
- continuation-after-pullback

  This provides the trend-side structure evidence.

### 4.2 Range / Mean Reversion / Chop Logic

  The same engine also evaluates the non-trending personality:

- range-state detection
- range duration and height
- breakout-follow probability
- false-break frequency
- reentry probability
- mean-reversion half-life
- z-score / band reentry rates
- choppiness and whipsaw metrics

  This provides the reversion-side evidence.

### 4.3 EDS Integration

  Market Structure also incorporates the two existing discovery studies as evidence inputs:

- EDS-2 Trend Persistence
- EDS-1 Mean Reversion

  Those are not the final verdict themselves. They are confirmation inputs into the broader structural model.

  Files:

- apps/edge/eds_trend_persistence.py
- apps/edge/eds_mean_reversion.py

  Important corrections were made here during development:

- EDS-1 now correctly records BUY trades
- range breakout logic uses prior range properly
- same-bar swing overcounting was fixed
- follow-through probability was redefined correctly from leg continuation logic

  ———

5. Market Structure Scoring Model

  The Market Structure model is now symmetric and more explicit.

  It computes:

- direction_score
- trend_confidence_score
- reversion_score
- reversion_confidence_score
- decision_confidence_score
- trend_bias_score
- reversion_bias_score
- final_score

  Conceptually:

- trend side = directional strength × trend confidence
- reversion side = reversion/chop strength × reversion confidence
- final score = trend bias minus reversion bias

  Then verdict becomes:

- TREND_BIASED
- REVERSION_BIASED
- MIXED

  The model now also has:

- model_version
- baseline_id

  These formally identify the current baseline configuration.

  ———

6. Profile Calibration, Stability, Robustness

  The model is no longer just a one-shot heuristic engine. It now includes research-quality support layers.

### 6.1 Profile-Specific Calibration

  Files:

- apps/edge/market_structure_profiles.py
- apps/edge/market_structure_profile_calibration.py

  Symbols are grouped into profile classes like:

- major FX
- JPY FX
- metals
- indices
- crypto
- other classes

  The engine can resolve profile-specific calibration overrides and apply them at runtime.

### 6.2 Regime Stability

  File:

- apps/edge/market_structure_stability.py

  The system now checks whether the verdict is stable across subperiods. It supports:

- early_middle_late
- monthly
- quarterly

  It computes:

- verdict agreement
- direction agreement
- score drift
- confidence drift
- stability label

  Low stability can now push the regime toward a transitional state.

### 6.3 Parameter Robustness

  File:

- apps/edge/market_structure_robustness.py

  The engine reruns nearby parameter variants across:

- swing window
- ATR threshold
- range window
- breakout horizon

  It computes:

- verdict agreement
- direction agreement
- score drift
- robustness label

  Robustness is now used as part of confidence, not direction.

  ———

7. Validation and Calibration Research Loop

  This is what makes the system more than a static scoring engine.

### 7.1 Persisted Evaluation Dataset

  Files:

- apps/edge/market_structure_validation.py
- apps/sqlite/schema.py
- apps/sqlite/edge_discovery.py

  Saved Market Structure runs can now be evaluated later against realized forward behavior. Persisted evaluations include:

- symbol
- timeframe
- run date
- predicted verdict
- component context
- realized forward behavior

  Realized targets include:

- continuation
- range reentry
- breakout failure
- chop / directional instability

### 7.2 Forward Validation

  The validation layer compares:

- predicted bias
- realized future outcome

  It supports breakdowns by:

- symbol
- timeframe
- verdict
- confidence bucket

### 7.3 Top-Level Calibration

  File:

- apps/edge/market_structure_calibration.py

  This calibrates top-level settings like:

- verdict gap
- confidence minimums
- reversion vs chop weighting

### 7.4 Metric-Band Calibration

  File:

- apps/edge/market_structure_metric_calibration.py

  This calibrates lower-level scoring bands like:

- chain strength
- pullback quality
- half-life
- choppiness
- false-break rates

  All of this is still simple grid-search style, intentionally not ML-heavy.

  ———

8. Tradeability Layer

  The bias verdict is kept separate from tradeability, which was the right design choice.

  The Market Structure page includes a separate tradeability overlay that evaluates whether the structural behavior is realistically exploitable. It
  includes first-pass metrics like:

- average spread
- spread/range burden
- session-specific spread burden
- rollover penalty
- volatility-adjusted spread burden
- liquidity/activity consistency

  This lets the system say:

- what the symbol is structurally
- whether that structure is easy or hard to trade

  without polluting the core bias classification.

  ———

9. Strategy-Fit Layer

  File:

- apps/edge/market_structure_strategy_fit.py

  On top of structural bias, the system now maps the symbol into strategy archetypes such as:

- breakout trend-following
- pullback continuation
- range fade
- mean-reversion fade
- avoid / choppy

  This is shown as a ranked recommendation layer in the Market Structure tab. So the system does not stop at “trend-biased”; it also says what kind
  of approach fits that structure best.

  ———

10. Persistence and API

  All of this is wired through the existing Edge Lab API and SQLite persistence layer.

  Backend route hub:

- apps/api/routes/edge.py

  Persistence hub:

- apps/sqlite/edge_discovery.py
- apps/sqlite/schema.py

  Saved Market Structure runs now persist:

- normalized values
- score rows
- swings
- legs
- calibration metadata

  Persisted evaluations now store the research dataset used by validation/calibration, rather than each endpoint inventing its own temporary sample.

  ———

11. UI Structure

  Edge Lab now works as a coherent system instead of unrelated pages.

  Current high-level UX:

- /edge-lab
  - Data tab / landing page
  - fetch, validate, clean, enrich, preview dataset
- /edge-lab/core-metric
  - basic statistics profile
- /edge-lab/discovery
  - EDS workflows
- /edge-lab/seasonality
  - seasonality on shared dataset
- /edge-lab/market-structure
  - structural bias engine and research layers

  Shared UI infrastructure includes:

- dataset session context
- dataset summary component
- collection/saved-run wrappers
- shared toggle/control components

  The Market Structure page itself now contains:

- research conclusion
- model quality
- strategy fit
- tradeability
- forward validation
- calibration snapshot
- metric calibration
- profile calibration
- stability snapshot
- robustness snapshot
- persisted evaluations
- Market Structure Edge Chart
- saved runs with view/delete
- calibration metadata visibility

  ———

12. Architecture State

  At this point, relative to the original roadmap, the system is complete at a first-pass research level.

  The original planned phases are covered:

- calibration baseline
- forward validation
- threshold calibration
- profile-specific calibration
- regime stability
- parameter robustness
- strategy fit
- tradeability
- reporting/UI

  The remaining work from here is not missing architecture. It is iterative refinement:

- collect more real runs
- tune thresholds on larger samples
- improve heuristics if the data says they should change

  In one sentence

  The full system is now a dataset-first, research-oriented market-structure framework that:

- prepares reliable OHLCVS data,
- classifies symbols as trend-biased, reversion-biased, or mixed,
- explains that verdict with audited structural evidence,
- recommends strategy archetypes,
- overlays tradeability,
- persists everything,
- and validates its own conclusions against later realized behavior.

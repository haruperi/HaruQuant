# HaruQuant Implementation Plan Mapped to Udacity AI Trading Strategies (ND881)

Status: canonical implementation plan
Scope: ND881 implementation scope, workstreams, milestones, and delivery order
Use this when: you need planning and sequencing
Companion docs: `../traceability/AI_Trading_Traceability.md`
Owner: program delivery
Review cadence: biweekly during active delivery

This is the canonical ND881 implementation plan for HaruQuant.

It supersedes earlier overlapping ND881 planning drafts and agentic extension
checklists that were consolidated into this document.

Use this document for:

- overall implementation scope
- workstreams
- phase delivery planning
- milestone planning
- implementation order

Use the traceability register for live status, lesson signoff, workflow signoff,
and final completion gates:

- `docs/haruquant/traceability/AI_Trading_Traceability.md`

**Purpose:**  
This document translates Udacity’s **AI Trading Strategies Nanodegree (ND881)** into a **comprehensive HaruQuant implementation plan**. Every major implementation item is explicitly associated with the corresponding **course and lesson** from the nanodegree so coverage can be audited and nothing is missed.

**Program basis used:**  
Udacity currently lists ND881 as **8 courses, 34 lessons, and 5 projects**, updated **March 26, 2026**. The core technical content spans:
- Building a Workflow for AI
- Preparing for Data Analysis
- Evaluating Returns and Backtesting
- Reinforcement Learning
- Optimizing AI Strategies
- Momentum-Based Trading

---

## 0. Current Coverage Snapshot

The plan is additive and assumes HaruQuant already has substantial reusable
infrastructure in place.

Current high-level coverage snapshot:

| ND881 Area | Existing HaruQuant Coverage | Status |
|---|---|---|
| C2: AI workflows | 5 workflow patterns, dynamic orchestrator, async workflows | complete |
| C3.L1: ML pipeline overview | middleware pipeline, workflow logs, workflow state | complete |
| C3.L3: feature engineering | context engineering, existing feature helpers | complete |
| C6.L5: deployment considerations | circuit breaker, approvals, risk governor, cost controls | complete |
| C6.L1: model optimization | edge lab optimization, Optuna, Monte Carlo | partial |
| C8: closeout foundations | strong workflow/docs/test base already in repo | complete |

Primary remaining build areas:

- data acquisition and preprocessing
- EDA and transformation workflows
- finance analytics and backtesting
- supervised ML training modules
- RL subsystem
- optimization hardening
- momentum subsystem
- unified reporting

## 1. Reference Key

Use this shorthand throughout the plan:

- **C1** = Course 1: Welcome to the Nanodegree Program!
- **C2** = Course 2: Building a Workflow for AI
- **C3** = Course 3: Preparing for Data Analysis
- **C4** = Course 4: Evaluating Returns and Backtesting
- **C5** = Course 5: Reinforcement Learning
- **C6** = Course 6: Optimizing AI Strategies
- **C7** = Course 7: Momentum-Based Trading
- **C8** = Course 8: Congratulations!

Lesson tags are written like:
- **C2.L1** = Course 2, Lesson 1
- **C4.L5** = Course 4, Project lesson
- **C7.L3** = Course 7, Lesson 3

---

## 2. Program Outline Used for Traceability

### C1 — Welcome to the Nanodegree Program!
- **C1.L1** Welcome!

### C2 — Building a Workflow for AI
- **C2.L1** Introduction to AI Workflows in Trading
- **C2.L2** Unsupervised Learning
- **C2.L3** Supervised Learning: Regression
- **C2.L4** Supervised Learning: Classification
- **C2.L5** Reinforcement Learning

### C3 — Preparing for Data Analysis
- **C3.L1** An Overview of Machine Learning Pipelines
- **C3.L2** Data Acquisition and Preprocessing
- **C3.L3** Feature Engineering for Trading Models
- **C3.L4** Exploratory Data Analysis
- **C3.L5** Project: Data Transformation for Trading Models

### C4 — Evaluating Returns and Backtesting
- **C4.L1** Measuring Returns
- **C4.L2** Measuring Risks
- **C4.L3** Measuring Risk-Adjusted Returns
- **C4.L4** Backtesting a Risk Parity Portfolio
- **C4.L5** Project: Evaluating and Backtesting a Dynamic Investment Strategy

### C5 — Reinforcement Learning
- **C5.L1** Reinforcement Learning in Trading
- **C5.L2** Representing the Financial Market: State and Action Spaces
- **C5.L3** Constructing a Reinforcement Trading Model
- **C5.L4** Backtesting and Optimization Techniques
- **C5.L5** Project: Building a Reinforcement Learning Trading Model

### C6 — Optimizing AI Strategies
- **C6.L1** Introduction to AI Model Optimization
- **C6.L2** Regularization Techniques to Prevent Overfitting
- **C6.L3** Hyperparameter Tuning Methods
- **C6.L4** Evaluating and Optimizing AI Strategies
- **C6.L5** Deployment and Real-World Considerations
- **C6.L6** Project: Building and Optimizing a Classification Model for Trading

### C7 — Momentum-Based Trading
- **C7.L1** What is Momentum-Based Trading
- **C7.L2** Identifying and Extracting Momentum Features
- **C7.L3** Constructing a Momentum Trading Model
- **C7.L4** Backtesting and Optimization Techniques
- **C7.L5** Project: Build a Momentum-Based Algorithmic Trading Program

### C8 — Congratulations!
- **C8.L1** Congratulations!

---

## 3. HaruQuant Target Outcome

By the end of this implementation plan, HaruQuant should be able to:

1. ingest and validate market data,
2. preprocess and transform data into model-ready datasets,
3. engineer features for statistical, supervised, unsupervised, and RL workflows,
4. run benchmark, ML, RL, and momentum strategies,
5. evaluate strategies using robust return/risk/risk-adjusted analytics,
6. optimize models while controlling overfitting,
7. monitor model drift and production health,
8. support reproducible research-to-deployment workflows.

This target directly reflects the nanodegree’s stated emphasis on **ideation, preprocessing, model development, backtesting, optimization, and model drift monitoring**.

---

## 4. Implementation Principles

1. **Traceability first**  
   Every implementation task must map to one or more lesson tags.

2. **Research-to-production continuity**  
   Notebook experiments are allowed, but all accepted logic must graduate into reusable library modules.

3. **Reproducibility as a hard requirement**  
   Every dataset, model run, optimization run, and backtest must be reproducible from config + code version + dataset hash.

4. **Separation of concerns**  
   Distinguish clearly between:
   - data ingestion,
   - preprocessing,
   - feature engineering,
   - model training,
   - backtesting,
   - optimization,
   - deployment monitoring.

5. **Evaluation before promotion**  
   No strategy should be promoted to paper/live pathways without:
   - OOS evaluation,
   - walk-forward validation where applicable,
   - risk analytics,
   - cost assumptions,
   - robustness checks.

---

## 5. Recommended Repository Structure

```text
haruquant/
  ai_workflow/
    workflow_runner.py
    experiment_config.py
    benchmarks.py
    labeling.py
    splits.py

  data/
    ingestion.py
    preprocessing.py
    validation.py
    sessions.py
    symbol_metadata.py

  features/
    technical.py
    statistical.py
    microstructure.py
    regime.py
    momentum.py
    portfolio.py
    registry.py

  eda/
    diagnostics.py
    plotting.py
    correlations.py
    drift_views.py

  ml/
    datasets.py
    unsupervised.py
    regression.py
    classification.py
    calibration.py
    evaluation.py

  backtest/
    engine.py
    broker.py
    position_sizer.py
    transaction_costs.py
    walk_forward.py
    portfolio.py

  finance/
    returns.py
    risks.py
    drawdowns.py
    ratios.py
    benchmark.py

  rl/
    environment.py
    state_builder.py
    action_space.py
    reward_functions.py
    q_learning.py
    dqn.py
    trainer.py
    evaluator.py

  optimization/
    search.py
    regularization.py
    feature_selection.py
    robustness.py
    stability.py
    registry.py
    drift_monitor.py

  strategies/
    baselines/
    classification_alpha/
    rl_strategy/
    momentum/

  reporting/
    report_builder.py
    dashboards/
    exports/

  live/
    paper_trading.py
    execution_bridge.py
    monitoring.py
```

---

## 6. Master Workstreams

The plan is organized into eight workstreams:

1. Program foundation and governance
2. AI workflow foundations
3. Data pipeline and preprocessing
4. Evaluation, returns, and backtesting
5. Reinforcement learning subsystem
6. Optimization and anti-overfitting subsystem
7. Momentum trading subsystem
8. Production hardening and final program closeout

---

# 7. Detailed Implementation Plan with Nanodegree Associations

---

## Workstream 1 — Program Foundation and Governance

### Objective
Create the foundations that let the rest of the nanodegree content be implemented in a maintainable, testable way.

### Tasks

#### 1.1 Define project scope, module boundaries, and naming conventions
**Associations:** `C1.L1`

**Tasks**
- Define HaruQuant subpackages for data, features, ML, RL, backtest, optimization, and live monitoring.
- Create naming rules for experiments, datasets, features, strategies, and model versions.
- Define required artifacts for every research run:
  - config,
  - data hash,
  - metrics JSON,
  - plots,
  - model artifact,
  - run notes.

**Outputs**
- `docs/ImplementationGovernance.md`
- `docs/ModuleOwnership.md`
- `docs/ExperimentNamingConvention.md`

#### 1.2 Create implementation traceability register
**Associations:** `C1.L1`, all later lessons

**Tasks**
- Build a simple markdown or CSV traceability register:
  - lesson tag,
  - lesson title,
  - HaruQuant module,
  - implementation status,
  - test status,
  - documentation status.
- Use it as the master audit checklist for full nanodegree coverage.

**Outputs**
- `docs/ND881_Traceability_Register.md`

---

## Workstream 2 — AI Workflow Foundations

### Objective
Implement a reusable AI trading workflow framework that supports baseline strategy research, supervised learning, unsupervised analysis, and early RL experimentation.

---

### 2.1 End-to-end AI workflow runner
**Associations:** `C2.L1`

**Tasks**
- Build a pipeline runner that supports:
  - dataset selection,
  - preprocessing pipeline selection,
  - feature set selection,
  - label selection,
  - train/validate/test split,
  - model training,
  - backtest integration,
  - report export.
- Support multiple run modes:
  - research,
  - benchmark comparison,
  - batch experiments,
  - walk-forward.

**Outputs**
- `haruquant/ai_workflow/workflow_runner.py`
- `haruquant/ai_workflow/experiment_config.py`

**Acceptance**
- One config file can trigger a full experiment from raw market data to report.

---

### 2.2 Baseline rule-based workflow for RSI and simple trading signals
**Associations:** `C2.L1`

**Tasks**
- Implement a simple RSI strategy benchmark.
- Add moving-average crossover and naive momentum baselines.
- Make them plug into the same backtest and reporting framework used by ML models.

**Outputs**
- `haruquant/ai_workflow/benchmarks.py`
- `haruquant/strategies/baselines/rsi.py`
- `haruquant/strategies/baselines/ema_cross.py`

**Acceptance**
- Baseline strategies produce the same metric/report outputs as AI-driven strategies.

---

### 2.3 Unsupervised research toolkit
**Associations:** `C2.L2`

**Tasks**
- Implement K-Means clustering for:
  - market regimes,
  - asset grouping,
  - feature space partitioning.
- Implement PCA for:
  - dimensionality reduction,
  - factor extraction,
  - regime visualization,
  - feature compression experiments.
- Add cluster/regime labeling outputs that can later be fed into supervised and RL workflows.
- Build exploratory notebooks or report sections to inspect:
  - cluster centroids,
  - explained variance,
  - risk factor interpretations.

**Outputs**
- `haruquant/ml/unsupervised.py`
- `haruquant/eda/correlations.py`
- `haruquant/features/regime.py`

**Acceptance**
- System can label market periods or asset snapshots into unsupervised clusters and use the result downstream.

---

### 2.4 Regression modeling framework
**Associations:** `C2.L3`

**Tasks**
- Implement target types:
  - next-bar return,
  - N-bar forward return,
  - rolling horizon return,
  - volatility forecast.
- Implement regression models:
  - linear regression,
  - ridge/lasso,
  - tree-based regressor baseline.
- Add training/test separation logic and overfitting diagnostics.
- Include residual analysis and prediction-vs-actual diagnostics.

**Outputs**
- `haruquant/ml/regression.py`
- `haruquant/ml/evaluation.py`

**Acceptance**
- Regression models can be trained from config and compared against baselines.

---

### 2.5 Classification modeling framework
**Associations:** `C2.L4`

**Tasks**
- Implement target types:
  - up/down classification,
  - multi-class return bucket,
  - signal/no-signal filters,
  - regime class prediction.
- Implement models:
  - logistic regression,
  - decision tree,
  - random forest or gradient-boosted tree baseline if desired.
- Add cross-validation and probability-threshold handling.
- Add confusion matrix, precision/recall/F1, ROC-AUC, and class-balance diagnostics.

**Outputs**
- `haruquant/ml/classification.py`
- `haruquant/ml/calibration.py`

**Acceptance**
- Classification model outputs can drive tradable signal generation via configurable probability thresholds.

---

### 2.6 Introductory RL bridge inside the AI workflow layer
**Associations:** `C2.L5`

**Tasks**
- Add a minimal adapter so the workflow system can trigger RL experiments, even before the full RL subsystem is completed.
- Define common interfaces for:
  - training,
  - inference,
  - policy evaluation,
  - backtest export.

**Outputs**
- `haruquant/ai_workflow/rl_adapter.py`

**Acceptance**
- RL can be run as another experiment mode from the same workflow command surface.

---

## Workstream 3 — Data Pipeline and Preprocessing

### Objective
Build the data engineering and feature engineering foundation required for all model classes.

---

### 3.1 Machine learning pipeline architecture
**Associations:** `C3.L1`

**Tasks**
- Define the canonical ML pipeline stages:
  1. ingest,
  2. validate,
  3. preprocess,
  4. feature-engineer,
  5. label,
  6. split,
  7. train,
  8. evaluate,
  9. backtest,
  10. export.
- Create interfaces so each stage can be swapped independently.
- Build stage-level metadata logging.

**Outputs**
- `docs/ML_Pipeline_Architecture.md`
- `haruquant/ai_workflow/pipeline_schema.py`

---

### 3.2 Data acquisition layer
**Associations:** `C3.L2`

**Tasks**
- Implement connectors or loaders for:
  - CSV/Parquet historical bars,
  - broker-exported tick data,
  - yfinance-style equity research data,
  - optional macro/event datasets.
- Normalize to canonical schema:
  - symbol,
  - timestamp,
  - open/high/low/close,
  - volume,
  - spread,
  - source,
  - timezone.
- Add ingestion metadata:
  - data source,
  - import timestamp,
  - missing segments,
  - trading session markers.

**Outputs**
- `haruquant/data/ingestion.py`
- `haruquant/data/symbol_metadata.py`

---

### 3.3 Preprocessing framework
**Associations:** `C3.L2`

**Tasks**
- Implement:
  - missing-value handling,
  - timezone normalization,
  - market session slicing,
  - duplicate timestamp detection,
  - outlier tagging,
  - stale-price detection,
  - spread anomaly detection.
- Support train-only scaling and transform application to validation/test sets.
- Add leakage-safe preprocessing patterns.

**Outputs**
- `haruquant/data/preprocessing.py`
- `haruquant/data/validation.py`
- `haruquant/data/sessions.py`

---

### 3.4 Feature engineering framework
**Associations:** `C3.L3`

**Tasks**
- Implement technical and statistical features:
  - returns,
  - log returns,
  - rolling volatility,
  - ATR/ADR,
  - RSI,
  - Williams %R,
  - MACD,
  - EMA spreads,
  - momentum windows,
  - z-scores,
  - rolling skew/kurtosis.
- Implement structure/context features:
  - candle body/range,
  - gap features,
  - session indicators,
  - regime labels,
  - cross-symbol relative strength.
- Add feature metadata registry:
  - feature name,
  - formula,
  - lookback,
  - lag,
  - leakage-safe flag,
  - owner module.

**Outputs**
- `haruquant/features/technical.py`
- `haruquant/features/statistical.py`
- `haruquant/features/registry.py`
- `haruquant/features/portfolio.py`

---

### 3.5 Exploratory data analysis toolkit
**Associations:** `C3.L4`

**Tasks**
- Implement reusable EDA routines:
  - return distributions,
  - rolling volatility plots,
  - cross-feature correlation heatmaps,
  - target-feature relationship plots,
  - regime segmentation views,
  - temporal drift comparisons,
  - missingness dashboards.
- Support notebook and report-friendly rendering.

**Outputs**
- `haruquant/eda/diagnostics.py`
- `haruquant/eda/plotting.py`
- `haruquant/eda/drift_views.py`

---

### 3.6 Project-grade data transformation workflow
**Associations:** `C3.L5`

**Tasks**
- Build a project-grade research example that:
  - ingests two or more instruments,
  - cleans and aligns them,
  - performs EDA,
  - exports transformed datasets,
  - documents assumptions.
- This should be a reusable internal reference implementation.

**Outputs**
- `examples/data_transformation_project.ipynb`
- `reports/sample_data_transformation_report.md`

**Acceptance**
- This example becomes the canonical “how to prep data correctly in HaruQuant” reference.

---

## Workstream 4 — Returns, Risk, and Backtesting

### Objective
Implement the full measurement and backtesting stack for strategy evaluation.

---

### 4.1 Returns analytics engine
**Associations:** `C4.L1`

**Tasks**
- Implement:
  - simple returns,
  - log returns,
  - cumulative returns,
  - annualized returns,
  - rolling returns,
  - benchmark-relative returns.
- Add charting for:
  - cumulative equity curve,
  - rolling return windows,
  - return distributions.

**Outputs**
- `haruquant/finance/returns.py`
- `haruquant/reporting/returns_report.py`

---

### 4.2 Risk analytics engine
**Associations:** `C4.L2`

**Tasks**
- Implement:
  - volatility,
  - downside deviation,
  - skewness,
  - kurtosis,
  - rolling risk windows,
  - exposure metrics,
  - concentration metrics,
  - holding-period distributions.
- Support both trade-level and portfolio-level risk calculations.

**Outputs**
- `haruquant/finance/risks.py`

---

### 4.3 Risk-adjusted performance engine
**Associations:** `C4.L3`

**Tasks**
- Implement:
  - drawdown series,
  - max drawdown,
  - average drawdown,
  - drawdown duration,
  - recovery duration,
  - Sharpe ratio,
  - Sortino ratio,
  - Calmar ratio,
  - information ratio if benchmark exists,
  - recovery factor.
- Support All / Long / Short splits.

**Outputs**
- `haruquant/finance/drawdowns.py`
- `haruquant/finance/ratios.py`

---

### 4.4 Risk parity portfolio and walk-forward backtesting
**Associations:** `C4.L4`

**Tasks**
- Implement portfolio backtest support for:
  - equal weight,
  - vol-scaled,
  - risk parity approximation,
  - constrained position sizing.
- Implement walk-forward validation:
  - anchored windows,
  - rolling windows,
  - train/test period generator,
  - parameter carry-forward handling.
- Add transaction cost modeling:
  - spread,
  - commission,
  - slippage,
  - optional swap placeholder.

**Outputs**
- `haruquant/backtest/portfolio.py`
- `haruquant/backtest/walk_forward.py`
- `haruquant/backtest/transaction_costs.py`
- `haruquant/backtest/position_sizer.py`

---

### 4.5 Dynamic investment strategy reference project
**Associations:** `C4.L5`

**Tasks**
- Build one full project-grade example strategy that uses:
  - dynamic allocation,
  - measured risk,
  - walk-forward validation,
  - performance reporting.
- Prefer a multi-asset or multi-symbol template so it becomes reusable for future strategies.

**Outputs**
- `examples/dynamic_investment_strategy_project.ipynb`
- `reports/sample_dynamic_strategy_report.md`

---

## Workstream 5 — Reinforcement Learning Subsystem

### Objective
Build a complete RL trading research subsystem aligned with the dedicated RL course.

---

### 5.1 RL foundations and trading abstraction
**Associations:** `C5.L1`

**Tasks**
- Define core RL abstractions:
  - environment,
  - state,
  - action,
  - reward,
  - episode,
  - policy,
  - exploration strategy.
- Document where RL fits relative to supervised and rule-based approaches in HaruQuant.
- Add a minimal Q-learning baseline spec.

**Outputs**
- `docs/RL_Architecture.md`
- `haruquant/rl/base.py`

---

### 5.2 Financial state and action space design
**Associations:** `C5.L2`

**Tasks**
- Implement state builder inputs:
  - recent price/return windows,
  - technical indicators,
  - volatility state,
  - regime cluster label,
  - open position state,
  - unrealized PnL,
  - risk budget state.
- Implement action spaces:
  - hold,
  - enter long,
  - enter short,
  - exit,
  - reduce,
  - reverse,
  - discrete allocation bucket.
- Build configurable action masks and constraints.

**Outputs**
- `haruquant/rl/state_builder.py`
- `haruquant/rl/action_space.py`

---

### 5.3 Reinforcement trading model construction
**Associations:** `C5.L3`

**Tasks**
- Build a training environment that supports:
  - episodic replay over historical data,
  - broker constraints,
  - trading costs,
  - reward calculation,
  - position transitions.
- Implement agents:
  - tabular Q-learning,
  - optional DQN baseline for richer state representation.
- Implement training loop:
  - epsilon-greedy exploration,
  - replay buffer for DQN if used,
  - episode summaries,
  - checkpointing.

**Outputs**
- `haruquant/rl/environment.py`
- `haruquant/rl/q_learning.py`
- `haruquant/rl/dqn.py`
- `haruquant/rl/trainer.py`

---

### 5.4 RL backtesting and optimization evaluation
**Associations:** `C5.L4`

**Tasks**
- Evaluate RL models on held-out periods.
- Capture:
  - total reward,
  - action frequency,
  - turnover,
  - cost sensitivity,
  - PnL,
  - drawdown,
  - Sharpe,
  - stability across seeds.
- Add reward-function comparison tools.
- Add state-feature ablation testing.

**Outputs**
- `haruquant/rl/evaluator.py`
- `reports/rl_evaluation_template.md`

---

### 5.5 Project-grade RL trading implementation
**Associations:** `C5.L5`

**Tasks**
- Create a reference project that trains a Q-learning-based trading agent from scratch on a defined dataset.
- Export:
  - training curves,
  - learned policy diagnostics,
  - OOS evaluation,
  - strategy report.

**Outputs**
- `examples/rl_trading_project.ipynb`
- `reports/sample_rl_project_report.md`

---

## Workstream 6 — Optimization and Anti-Overfitting

### Objective
Build a comprehensive optimization subsystem with explicit safeguards against overfitting and production decay.

---

### 6.1 AI model optimization architecture
**Associations:** `C6.L1`

**Tasks**
- Define optimization objectives:
  - predictive metrics,
  - strategy metrics,
  - multi-objective score.
- Define optimization targets by model class:
  - regression,
  - classification,
  - RL,
  - momentum model.
- Standardize optimization experiment logging.

**Outputs**
- `docs/Optimization_Architecture.md`
- `haruquant/optimization/objectives.py`

---

### 6.2 Regularization and overfitting controls
**Associations:** `C6.L2`

**Tasks**
- Implement regularization support for:
  - ridge/lasso,
  - early stopping,
  - max tree depth,
  - min samples per leaf,
  - dropout/weight decay if neural models are used.
- Add model complexity diagnostics:
  - training vs validation gap,
  - learning curves,
  - bias/variance analysis,
  - overfit flagging rules.

**Outputs**
- `haruquant/optimization/regularization.py`
- `haruquant/optimization/stability.py`

---

### 6.3 Hyperparameter tuning framework
**Associations:** `C6.L3`

**Tasks**
- Implement:
  - grid search,
  - random search,
  - optional Bayesian optimization,
  - manual override tuning profiles.
- Support:
  - time-series-aware CV,
  - walk-forward-aware optimization,
  - parallel search execution.

**Outputs**
- `haruquant/optimization/search.py`

---

### 6.4 Strategy evaluation and optimization loop
**Associations:** `C6.L4`

**Tasks**
- Implement a promote/reject evaluation gate using:
  - predictive metrics,
  - OOS results,
  - risk-adjusted returns,
  - cost sensitivity,
  - parameter stability,
  - drawdown thresholds.
- Add feature importance and ablation workflows.
- Add robustness tests:
  - shuffled trade order,
  - slippage stress,
  - spread stress,
  - data perturbation,
  - regime split evaluation.

**Outputs**
- `haruquant/optimization/robustness.py`
- `haruquant/optimization/feature_selection.py`

---

### 6.5 Deployment and real-world production considerations
**Associations:** `C6.L5`

**Tasks**
- Implement model registry:
  - model ID,
  - training data range,
  - feature version,
  - hyperparameters,
  - evaluation summary,
  - promotion status.
- Implement drift monitoring:
  - feature drift,
  - target drift proxy,
  - prediction drift,
  - live-vs-backtest divergence.
- Implement production health alerts:
  - latency,
  - missing input features,
  - confidence collapse,
  - risk limit breach.

**Outputs**
- `haruquant/optimization/registry.py`
- `haruquant/optimization/drift_monitor.py`
- `haruquant/live/monitoring.py`

---

### 6.6 Project-grade classification model optimization workflow
**Associations:** `C6.L6`

**Tasks**
- Build an end-to-end classification model project that includes:
  - preprocessing,
  - feature selection,
  - hyperparameter tuning,
  - overfitting detection,
  - evaluation,
  - report export.
- Use it as the internal template for all future classification strategies.

**Outputs**
- `examples/classification_optimization_project.ipynb`
- `reports/sample_classification_optimization_report.md`

---

## Workstream 7 — Momentum Trading Subsystem

### Objective
Implement a dedicated momentum strategy research and execution package aligned with the nanodegree’s momentum course.

---

### 7.1 Momentum foundations and statistical toolkit
**Associations:** `C7.L1`

**Tasks**
- Implement statistical helpers for momentum research:
  - normality diagnostics,
  - Shapiro-Wilk test wrapper,
  - Student’s t-test helper,
  - distribution summaries,
  - return significance tests.
- Document where momentum models fit within HaruQuant’s strategy taxonomy.

**Outputs**
- `haruquant/strategies/momentum/stats.py`
- `docs/Momentum_Research_Framework.md`

---

### 7.2 Momentum feature extraction and stochastic modeling
**Associations:** `C7.L2`

**Tasks**
- Implement momentum features:
  - time-series momentum,
  - cross-sectional momentum,
  - breakout distance,
  - rolling trend persistence,
  - volatility-adjusted momentum.
- Implement geometric Brownian motion helpers for:
  - calibration,
  - forecasting,
  - confidence intervals.
- Add optional analytical helpers for option-aware research such as Black-Scholes reference functions when useful.

**Outputs**
- `haruquant/features/momentum.py`
- `haruquant/strategies/momentum/gbm.py`
- `haruquant/strategies/momentum/confidence_intervals.py`

---

### 7.3 Momentum trading model construction
**Associations:** `C7.L3`

**Tasks**
- Build a momentum strategy engine that supports:
  - ranking,
  - selection,
  - holding period rules,
  - rebalance schedules,
  - confidence-filtered entries,
  - scenario simulation.
- Support SQLite/MySQL-backed research runs if desired for parity with course framing.
- Add Monte Carlo scenario simulation hooks.

**Outputs**
- `haruquant/strategies/momentum/model.py`
- `haruquant/strategies/momentum/scenario_sim.py`

---

### 7.4 Momentum backtesting and optimization
**Associations:** `C7.L4`

**Tasks**
- Evaluate momentum strategies with:
  - Sharpe ratio,
  - max drawdown,
  - turnover,
  - hit ratio,
  - regime sensitivity.
- Implement VaR and Expected Shortfall overlays.
- Add optimization of:
  - lookback windows,
  - rebalance frequency,
  - ranking thresholds,
  - volatility filters.

**Outputs**
- `haruquant/strategies/momentum/risk.py`
- `haruquant/strategies/momentum/backtest.py`

---

### 7.5 Project-grade momentum trading program
**Associations:** `C7.L5`

**Tasks**
- Create one flagship momentum strategy project.
- The project should be directly runnable and include:
  - feature extraction,
  - model construction,
  - scenario simulation,
  - risk overlays,
  - backtest,
  - report.
- Include one equity-focused example and one FX-adapted example if possible.

**Outputs**
- `examples/momentum_trading_project.ipynb`
- `reports/sample_momentum_project_report.md`

---

## Workstream 8 — Production Hardening and Closeout

### Objective
Turn the educational implementation into an operational subsystem and complete the nanodegree coverage loop.

---

### 8.1 Unified reporting layer
**Associations:** `C4.L1`, `C4.L2`, `C4.L3`, `C5.L4`, `C6.L4`, `C7.L4`

**Tasks**
- Build a shared reporting layer that can output:
  - HTML/Markdown reports,
  - CSV metrics summaries,
  - plots,
  - model cards,
  - strategy cards.
- Standardize sections:
  - dataset summary,
  - feature summary,
  - training summary,
  - predictive metrics,
  - strategy metrics,
  - risk metrics,
  - caveats,
  - promotion verdict.

**Outputs**
- `haruquant/reporting/report_builder.py`

---

### 8.2 Testing framework
**Associations:** all technical lessons

**Tasks**
- Create test layers:
  - unit tests for formulas,
  - property tests for transformations,
  - integration tests for training pipelines,
  - regression tests for metrics outputs,
  - smoke tests for end-to-end project templates.
- Add reproducibility tests for deterministic pipelines where possible.

**Outputs**
- `tests/`

---

### 8.3 Paper-trading bridge
**Associations:** `C4.L5`, `C5.L4`, `C6.L5`, `C7.L4`

**Tasks**
- Add a paper-trading adapter for promoted strategies.
- Make sure all promoted models expose a standard inference API.
- Log:
  - live predictions,
  - actual outcomes,
  - drift metrics,
  - risk breaches,
  - execution gaps.

**Outputs**
- `haruquant/live/paper_trading.py`
- `haruquant/live/execution_bridge.py`

---

### 8.4 Final review and graduation checklist
**Associations:** `C8.L1`

**Tasks**
- Review lesson-by-lesson coverage.
- Confirm all project-grade reference implementations exist.
- Create a final subsystem readiness checklist:
  - data readiness,
  - model readiness,
  - backtest readiness,
  - optimization readiness,
  - production readiness.

**Outputs**
- `docs/ND881_Final_Coverage_Checklist.md`
- `docs/HaruQuant_AI_Trading_Subsystem_Readiness.md`

---

# 8. Phase-Based Delivery Plan

## Phase 0 — Governance and skeleton
**Primary tags:** `C1.L1`

**Deliver**
- repo structure,
- traceability register,
- experiment naming,
- governance docs.

---

## Phase 1 — Workflow and baseline research
**Primary tags:** `C2.L1`, `C2.L2`, `C2.L3`, `C2.L4`, `C2.L5`

**Deliver**
- workflow runner,
- baseline RSI,
- unsupervised tools,
- regression module,
- classification module,
- RL adapter.

---

## Phase 2 — Data engineering and feature layer
**Primary tags:** `C3.L1`, `C3.L2`, `C3.L3`, `C3.L4`, `C3.L5`

**Deliver**
- ingestion,
- preprocessing,
- validation,
- feature registry,
- EDA toolkit,
- transformation reference project.

---

## Phase 3 — Returns, risk, and backtesting
**Primary tags:** `C4.L1`, `C4.L2`, `C4.L3`, `C4.L4`, `C4.L5`

**Deliver**
- returns module,
- risk module,
- ratios module,
- portfolio backtester,
- walk-forward engine,
- dynamic strategy reference project.

---

## Phase 4 — Reinforcement learning
**Primary tags:** `C5.L1`, `C5.L2`, `C5.L3`, `C5.L4`, `C5.L5`

**Deliver**
- RL environment,
- state/action space,
- Q-learning,
- optional DQN,
- RL evaluator,
- RL reference project.

---

## Phase 5 — Optimization and deployment-readiness
**Primary tags:** `C6.L1`, `C6.L2`, `C6.L3`, `C6.L4`, `C6.L5`, `C6.L6`

**Deliver**
- optimization objectives,
- regularization,
- hyperparameter search,
- robustness suite,
- drift monitor,
- classification optimization project.

---

## Phase 6 — Momentum subsystem
**Primary tags:** `C7.L1`, `C7.L2`, `C7.L3`, `C7.L4`, `C7.L5`

**Deliver**
- momentum statistical toolkit,
- momentum features,
- GBM helpers,
- momentum model,
- VaR/ES overlays,
- flagship momentum project.

---

## Phase 7 — Production hardening and closeout
**Primary tags:** `C8.L1` plus cross-course production items

**Deliver**
- unified reporting,
- testing suite,
- paper-trading bridge,
- final coverage audit.

---

# 9. Suggested 16-Week Schedule

## Weeks 1–2
- Governance and traceability
- Workflow runner
- Baseline RSI and benchmark strategies
- Initial unsupervised toolkit

**Tags:** `C1.L1`, `C2.L1`, `C2.L2`

## Weeks 3–4
- Regression and classification modules
- Core ML pipeline definition
- Data ingestion and preprocessing

**Tags:** `C2.L3`, `C2.L4`, `C3.L1`, `C3.L2`

## Weeks 5–6
- Feature engineering
- EDA toolkit
- Data transformation project template

**Tags:** `C3.L3`, `C3.L4`, `C3.L5`

## Weeks 7–8
- Returns, risk, drawdowns, ratios
- Walk-forward and portfolio backtester
- Dynamic strategy project

**Tags:** `C4.L1`, `C4.L2`, `C4.L3`, `C4.L4`, `C4.L5`

## Weeks 9–11
- RL architecture
- State/action spaces
- Q-learning / DQN prototype
- RL evaluator and RL reference project

**Tags:** `C5.L1`, `C5.L2`, `C5.L3`, `C5.L4`, `C5.L5`

## Weeks 12–13
- Regularization
- Hyperparameter tuning
- Robustness suite
- Drift monitoring
- Classification optimization project

**Tags:** `C6.L1`, `C6.L2`, `C6.L3`, `C6.L4`, `C6.L5`, `C6.L6`

## Weeks 14–15
- Momentum statistics and features
- GBM forecasting helpers
- Momentum model and risk overlays
- Momentum project

**Tags:** `C7.L1`, `C7.L2`, `C7.L3`, `C7.L4`, `C7.L5`

## Week 16
- Unified reporting
- Paper trading adapter
- Final coverage review and readiness signoff

**Tags:** `C8.L1` and cross-cutting review

---

# 10. Lesson-by-Lesson Coverage Matrix

| Lesson Tag | Lesson Title | HaruQuant Implementation Coverage |
|---|---|---|
| C1.L1 | Welcome! | Governance, repo structure, traceability register, program kickoff docs |
| C2.L1 | Introduction to AI Workflows in Trading | Workflow runner, RSI baseline, benchmark strategy orchestration |
| C2.L2 | Unsupervised Learning | K-Means, PCA, clustering/regime labeling, factor exploration |
| C2.L3 | Supervised Learning: Regression | Return prediction targets, regression models, overfit diagnostics |
| C2.L4 | Supervised Learning: Classification | Logistic/Tree classifiers, CV, thresholding, signal generation |
| C2.L5 | Reinforcement Learning | RL adapter and workflow integration entry point |
| C3.L1 | An Overview of Machine Learning Pipelines | Canonical ML pipeline architecture and stage interfaces |
| C3.L2 | Data Acquisition and Preprocessing | Ingestion, wrangling, normalization, validation, leakage-safe transforms |
| C3.L3 | Feature Engineering for Trading Models | Technical/statistical/context features + feature registry |
| C3.L4 | Exploratory Data Analysis | Diagnostic plots, correlations, drift comparisons, distribution analysis |
| C3.L5 | Project: Data Transformation for Trading Models | Reference transformation project and reusable data-prep example |
| C4.L1 | Measuring Returns | Return formulas, cumulative return plots, rolling return views |
| C4.L2 | Measuring Risks | Volatility, skew, kurtosis, exposure, concentration analytics |
| C4.L3 | Measuring Risk-Adjusted Returns | Drawdowns, Sharpe, Sortino, Calmar, recovery analytics |
| C4.L4 | Backtesting a Risk Parity Portfolio | Portfolio engine, walk-forward, vol-scaled/risk parity allocation |
| C4.L5 | Project: Evaluating and Backtesting a Dynamic Investment Strategy | Full dynamic strategy case study with walk-forward and risk metrics |
| C5.L1 | Reinforcement Learning in Trading | RL architecture and conceptual placement in HaruQuant |
| C5.L2 | Representing the Financial Market: State and Action Spaces | State builder, action space, position/risk-aware state design |
| C5.L3 | Constructing a Reinforcement Trading Model | Environment, training loop, Q-learning, optional DQN |
| C5.L4 | Backtesting and Optimization Techniques | RL evaluation harness, reward comparisons, OOS performance review |
| C5.L5 | Project: Building a Reinforcement Learning Trading Model | End-to-end RL reference project |
| C6.L1 | Introduction to AI Model Optimization | Optimization architecture and experiment objectives |
| C6.L2 | Regularization Techniques to Prevent Overfitting | Regularization, bias/variance diagnostics, complexity controls |
| C6.L3 | Hyperparameter Tuning Methods | Grid/random/Bayesian search with time-series aware evaluation |
| C6.L4 | Evaluating and Optimizing AI Strategies | Promotion gates, robustness suite, feature ablation, stability tests |
| C6.L5 | Deployment and Real-World Considerations | Model registry, drift monitoring, production alerts, paper-trade readiness |
| C6.L6 | Project: Building and Optimizing a Classification Model for Trading | Full classification optimization template project |
| C7.L1 | What is Momentum-Based Trading | Statistical toolkit, significance testing, momentum research framing |
| C7.L2 | Identifying and Extracting Momentum Features | Momentum features, GBM, confidence intervals, optional option-aware helpers |
| C7.L3 | Constructing a Momentum Trading Model | Ranking engine, selection logic, scenario simulation |
| C7.L4 | Backtesting and Optimization Techniques | Momentum backtest analytics, VaR, ES, optimization loops |
| C7.L5 | Project: Build a Momentum-Based Algorithmic Trading Program | Full momentum flagship project |
| C8.L1 | Congratulations! | Final readiness review, lesson coverage audit, subsystem signoff |

---

# 11. Non-Negotiable Acceptance Gates

A work item is not complete unless all of the following are true:

1. **Code exists**
- Implemented in reusable module form, not only notebook form.

2. **Tests exist**
- Formula correctness, transformation behavior, and integration path coverage.

3. **Documentation exists**
- README or internal design note for the module.

4. **Traceability is updated**
- Lesson tags and implementation status updated in the register.

5. **Report artifact exists**
- Example output proving the module works.

---

# 12. High-Priority Milestones

## Milestone A — Research-ready core
**Covers:** `C1`, `C2`, `C3`
- workflow runner,
- baseline models,
- ingestion,
- preprocessing,
- features,
- EDA.

## Milestone B — Evaluation-ready trading engine
**Covers:** `C4`
- returns/risk/ratios,
- walk-forward,
- portfolio backtesting,
- dynamic strategy reference.

## Milestone C — RL research capability
**Covers:** `C5`
- RL environment,
- state/action design,
- Q-learning/DQN,
- RL project.

## Milestone D — Optimization and production control
**Covers:** `C6`
- regularization,
- tuning,
- robustness,
- drift,
- registry,
- classification project.

## Milestone E — Momentum flagship subsystem
**Covers:** `C7`
- momentum features,
- stochastic modeling helpers,
- momentum strategy,
- VaR/ES,
- flagship project.

## Milestone F — Full ND881 coverage signoff
**Covers:** `C8`
- reporting,
- paper trading,
- final coverage review,
- readiness signoff.

---

# 13. Final Completion Definition

This ND881-aligned implementation plan is complete when:

- every lesson tag from **C1.L1** through **C8.L1** is marked covered,
- all five project-style reference implementations exist,
- all core subsystems are modularized in HaruQuant,
- reporting and traceability are in place,
- at least one strategy each exists for:
  - baseline/rule-based,
  - supervised classification or regression,
  - reinforcement learning,
  - momentum,
- promotion gates and drift monitoring are operational.

---

# 14. Source Basis

This implementation plan is based on the official Udacity **AI Trading Strategies (ND881)** program page, which currently lists:
- **8 courses**
- **34 lessons**
- **5 projects**
- updated **March 26, 2026**

Core course/lesson wording used in this document was taken from the program outline to preserve traceability accuracy.

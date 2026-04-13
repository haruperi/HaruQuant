# HaruQuant ND881 Implementation Checklist

**Purpose:** Task-by-task checklist for implementing all 16 remaining ND881 lessons on top of the 18 already-complete lessons.
**Total tasks:** 53 (16 new lessons × ~3–4 tasks each + reference projects)
**Already complete:** 18/34 lessons (marked ✅ below)
**Target:** 34/34 lessons covered

---

## ✅ Already Complete — No Action Needed (18 Lessons)

- [x] **C2.L1** — AI Workflows in Trading (5 workflow patterns + DynamicOrchestrator)
- [x] **C2.L2** — Unsupervised Learning (regime detection via regime_agent)
- [x] **C2.L3** — Supervised: Regression *(framework ready, ML module needs building → see Workstream 2 below)*
- [x] **C2.L4** — Supervised: Classification *(framework ready, ML module needs building → see Workstream 2 below)*
- [x] **C2.L5** — Reinforcement Learning (ReAct agent)
- [x] **C3.L1** — ML Pipeline Overview (MiddlewarePipeline, 5 layers)
- [x] **C3.L3** — Feature Engineering (context engineering, 68+ features)
- [x] **C6.L1** — Model Optimization (edge lab, Optuna, Monte Carlo)
- [x] **C6.L5** — Deployment Considerations (circuit breaker, cost enforcer, approval packets)
- [x] **C8.L1** — Congratulations (10/10 workflow score, 258 tests, 38 docs)

> **Note:** C2.L3, C2.L4 are marked "framework ready" because the infrastructure exists (agents, contracts, workflows, validation) but the scikit-learn ML training modules themselves need to be built in Workstream 2.

---

## Workstream 1 — Data Pipeline & Preprocessing

### C3.L2: Data Acquisition and Preprocessing

- [ ] **1.1** CSV/Parquet data loaders with canonical OHLCV schema
  - **File:** `backend/ai_trading/data/ingestion.py`
  - **Builds on:** `backend/data/database/repositories/` — same SQLite patterns
  - **Acceptance:** Ingest → validate → store in canonical format (symbol, timestamp, OHLCV, volume, spread, source, timezone)

- [ ] **1.2** Missing value, outlier, and duplicate timestamp detection
  - **File:** `backend/ai_trading/data/preprocessing.py`
  - **Builds on:** `backend/agents/runtime/middleware.py` — same pipeline pattern
  - **Acceptance:** Leakage-safe preprocessing with train/test separation; stale-price and spread anomaly detection

- [ ] **1.3** Market session slicing and timezone normalization
  - **File:** `backend/ai_trading/data/validation.py`
  - **Builds on:** `backend/orchestration/context_engineering/` — same context awareness
  - **Acceptance:** Session markers applied to all OHLCV data; trading hours correctly identified

### C3.L4: Exploratory Data Analysis

- [ ] **1.4** Return distributions and rolling volatility plots
  - **File:** `backend/ai_trading/reporting/report_builder.py`
  - **Builds on:** `backend/observability/trace_model.py` — same structured logging
  - **Acceptance:** Reusable EDA routines for notebooks and reports

- [ ] **1.5** Cross-feature correlation heatmaps and temporal drift comparisons
  - **File:** `backend/ai_trading/reporting/report_builder.py`
  - **Builds on:** `backend/orchestration/context_engineering/contradiction.py` — same correlation logic
  - **Acceptance:** Drift comparison views for temporal analysis; correlation matrix exportable

### C3.L5: Data Transformation Reference Project

- [ ] **1.6** End-to-end ingestion → EDA → transformed dataset export script
  - **File:** `backend/scripts/examples/ai_trading/01_data_transformation.py`
  - **Builds on:** `backend/scripts/examples/agentic_ai/` — same example pattern
  - **Acceptance:** Runnable script that ingests ≥2 instruments, cleans, aligns, performs EDA, exports transformed datasets, and produces a report artifact

---

## Workstream 2 — ML Training (Regression & Classification)

### C2.L3: Supervised Learning — Regression

- [ ] **2.1** Target type builder: next-bar return, N-bar forward return, volatility forecast
  - **File:** `backend/ai_trading/ml/datasets.py`
  - **Builds on:** `backend/contracts/observation_event.py` — same contract schema
  - **Acceptance:** Dataset builder produces labeled train/validate/test splits with no leakage

- [ ] **2.2** Regression models: linear, ridge/lasso, tree-based
  - **File:** `backend/ai_trading/ml/regression.py`
  - **Builds on:** `backend/agents/runtime/litellm_runtime.py` — same model abstraction
  - **Acceptance:** Regressors trainable from config; outputs comparable to baselines

- [ ] **2.3** Residual analysis and prediction-vs-actual diagnostics
  - **File:** `backend/ai_trading/ml/evaluation.py`
  - **Builds on:** `backend/observability/cost_tracker.py` — same metrics tracking
  - **Acceptance:** Overfitting diagnostics with train/validation gap reporting

### C2.L4: Supervised Learning — Classification

- [ ] **2.4** Classification target types: up/down, multi-class, signal/no-signal
  - **File:** `backend/ai_trading/ml/datasets.py`
  - **Builds on:** `backend/contracts/trade_hypothesis.py` — same contract-driven design
  - **Acceptance:** Classification targets derived from contract payloads; configurable thresholds

- [ ] **2.5** Classification models: logistic regression, decision tree, random forest
  - **File:** `backend/ai_trading/ml/classification.py`
  - **Builds on:** `backend/agents/runtime/output_validation.py` — same validation pattern
  - **Acceptance:** Models produce probability outputs; cross-validation supported

- [ ] **2.6** Evaluation metrics: confusion matrix, ROC-AUC, precision/recall/F1
  - **File:** `backend/ai_trading/ml/evaluation.py`
  - **Builds on:** `backend/agents/runtime/workflow_log.py` — same structured logging
  - **Acceptance:** Evaluation report with all standard classification metrics

- [ ] **2.7** Probability calibration and thresholding for signal generation
  - **File:** `backend/ai_trading/ml/calibration.py`
  - **Builds on:** `backend/agents/prompts/` — same threshold-based decision patterns
  - **Acceptance:** Calibrated probabilities drive tradable signal generation via configurable thresholds

### C6.L6: Classification Optimization Reference Project

- [ ] **2.8** End-to-end classification optimization script
  - **File:** `backend/scripts/examples/ai_trading/02_classification_optimization.py`
  - **Builds on:** `backend/scripts/examples/agentic_ai/02_agentic_workflows.py` — same multi-phase pattern
  - **Acceptance:** Runnable script: preprocessing → feature selection → tuning → evaluation → strategy card report

---

## Workstream 3 — Finance Analytics & Backtesting

### C4.L1: Measuring Returns

- [ ] **3.1** Returns engine: simple, log, cumulative, annualized, rolling returns
  - **File:** `backend/ai_trading/finance/returns.py`
  - **Builds on:** `backend/contracts/execution_receipt.py` — same trade data schema
  - **Acceptance:** Returns engine produces all standard return metrics; chart-ready output

### C4.L2: Measuring Risks

- [ ] **3.2** Risk engine: volatility, downside deviation, skewness, kurtosis
  - **File:** `backend/ai_trading/finance/risks.py`
  - **Builds on:** `backend/agents/risk_governor_agent/` — same risk computation patterns
  - **Acceptance:** Risk analytics match risk_governor_agent outputs; trade-level and portfolio-level calculations

### C4.L3: Risk-Adjusted Returns

- [ ] **3.3** Drawdown analytics: series, max DD, avg DD, recovery duration
  - **File:** `backend/ai_trading/finance/drawdowns.py`
  - **Builds on:** `backend/agents/drawdown_agent/` — same drawdown analysis
  - **Acceptance:** Drawdown analytics match existing drawdown_agent outputs

- [ ] **3.4** Risk-adjusted ratios: Sharpe, Sortino, Calmar, information ratio
  - **File:** `backend/ai_trading/finance/ratios.py`
  - **Builds on:** `backend/observability/cost_tracker.py` — same per-trace tracking
  - **Acceptance:** Risk-adjusted ratios per strategy and per trace; All/Long/Short splits

### C4.L4: Backtesting Engine

- [ ] **3.5** Event-driven backtest engine with simulated broker (fills, rejections)
  - **File:** `backend/ai_trading/backtest/engine.py`, `broker.py`
  - **Builds on:** `backend/agents/execution_agent/` — same execution intent pattern
  - **Acceptance:** Backtest produces execution receipts matching live format

- [ ] **3.6** Position sizing: fixed, Kelly, vol-scaled, risk-parity
  - **File:** `backend/ai_trading/backtest/position_sizer.py`
  - **Builds on:** `backend/agents/portfolio_agent/` — same portfolio math
  - **Acceptance:** Sizers plug into existing portfolio contracts

- [ ] **3.7** Transaction costs: spread, commission, slippage modeling
  - **File:** `backend/ai_trading/backtest/transaction_costs.py`
  - **Builds on:** `backend/observability/cost_tracker.py` — same cost tracking
  - **Acceptance:** Cost assumptions tracked and reported per trade

- [ ] **3.8** Walk-forward validation: anchored/rolling window generator
  - **File:** `backend/ai_trading/backtest/walk_forward.py`
  - **Builds on:** `backend/agents/runtime/workflows.py` — same workflow pattern
  - **Acceptance:** Walk-forward as a workflow pattern composition; parameter carry-forward handled

- [ ] **3.9** Multi-asset portfolio backtesting
  - **File:** `backend/ai_trading/backtest/portfolio.py`
  - **Builds on:** `backend/orchestration/workflow/executor.py` — same execution model
  - **Acceptance:** Portfolio backtest produces same report format as single-asset

### C4.L5: Dynamic Investment Strategy Reference Project

- [ ] **3.10** End-to-end dynamic strategy script
  - **File:** `backend/scripts/examples/ai_trading/03_dynamic_strategy.py`
  - **Builds on:** `backend/scripts/examples/agentic_ai/` — same example framework
  - **Acceptance:** Runnable: dynamic allocation + measured risk + walk-forward + report artifact

---

## Workstream 4 — Reinforcement Learning

### C5.L1: RL Foundations

- [ ] **4.1** RL architecture document — placement relative to supervised/rule-based
  - **File:** `backend/ai_trading/rl/base.py`
  - **Builds on:** `backend/agents/react/react_agent.py` — same agent loop pattern
  - **Acceptance:** RL documented as another agent type in the runtime

### C5.L2: State and Action Space Design

- [ ] **4.2** State builder: price windows, indicators, regime, PnL, risk budget
  - **File:** `backend/ai_trading/rl/state_builder.py`
  - **Builds on:** `backend/orchestration/context_engineering/` — same context composition
  - **Acceptance:** State composed from existing features + memory + regime labels

- [ ] **4.3** Action space: hold, enter/exit long/short, reduce, reverse
  - **File:** `backend/ai_trading/rl/action_space.py`
  - **Builds on:** `backend/agents/execution_agent/` — same execution intent contracts
  - **Acceptance:** Actions mapped to `ExecutionIntent` contracts; configurable masks and constraints

### C5.L3: RL Trading Model Construction

- [ ] **4.4** Trading environment with broker constraints, costs, reward calculation
  - **File:** `backend/ai_trading/rl/environment.py`
  - **Builds on:** `backend/ai_trading/backtest/engine.py` — same backtest engine
  - **Acceptance:** Environment reuses backtest engine as the world simulator

- [ ] **4.5** Reward functions: PnL, Sharpe, drawdown-penalized, risk-adjusted
  - **File:** `backend/ai_trading/rl/reward_functions.py`
  - **Builds on:** `backend/ai_trading/finance/ratios.py` — same Sharpe/Drawdown logic
  - **Acceptance:** Rewards compose existing finance analytics; configurable reward design

- [ ] **4.6** Tabular Q-learning agent
  - **File:** `backend/ai_trading/rl/q_learning.py`
  - **Builds on:** `backend/agents/react/react_agent.py` — same step loop
  - **Acceptance:** Q-learning as a specialized agent runtime; epsilon-greedy exploration

- [ ] **4.7** DQN agent (optional)
  - **File:** `backend/ai_trading/rl/dqn.py`
  - **Builds on:** `backend/agents/runtime/litellm_runtime.py` — same model abstraction
  - **Acceptance:** DQN as alternative to tabular Q-learning; replay buffer, target network

- [ ] **4.8** Training loop: episodes, replay buffer, checkpointing
  - **File:** `backend/ai_trading/rl/trainer.py`
  - **Builds on:** `backend/agents/runtime/workflow_state.py` — same checkpoint persistence
  - **Acceptance:** Training checkpoints saved to same SQLite store; episode summaries exported

### C5.L4: RL Evaluation

- [ ] **4.9** OOS evaluation, reward comparison, seed stability analysis
  - **File:** `backend/ai_trading/rl/evaluator.py`
  - **Builds on:** `backend/agents/runtime/workflow_log.py` — same execution logging
  - **Acceptance:** RL evaluator produces same report format as ML evaluator

- [ ] **4.10** Action frequency, turnover, cost sensitivity diagnostics
  - **File:** `backend/ai_trading/rl/evaluator.py`
  - **Builds on:** `backend/observability/cost_tracker.py` — same per-action cost tracking
  - **Acceptance:** Cost-per-action breakdown in RL reports; state-feature ablation testing

### C5.L5: RL Reference Project

- [ ] **4.11** End-to-end RL trading script
  - **File:** `backend/scripts/examples/ai_trading/04_rl_trading.py`
  - **Builds on:** `backend/scripts/examples/agentic_ai/` — same example framework
  - **Acceptance:** Runnable: train Q-learning → OOS evaluation → training curves → strategy report

---

## Workstream 5 — Momentum Subsystem

### C7.L1: Momentum Foundations

- [ ] **5.1** Statistical helpers: Shapiro-Wilk, t-test, distribution summaries
  - **File:** `backend/ai_trading/strategies/momentum/stats.py`
  - **Builds on:** `backend/orchestration/context_engineering/validator.py` — same validation patterns
  - **Acceptance:** Statistical tests for return significance; normality diagnostics

- [ ] **5.2** Momentum strategy taxonomy document
  - **File:** `docs/ai_trading/Momentum_Framework.md`
  - **Builds on:** `docs/agentic_ai/` — same documentation patterns
  - **Acceptance:** Documented where momentum fits in strategy taxonomy

### C7.L2: Momentum Features

- [ ] **5.3** Momentum features: time-series, cross-sectional, breakout, volatility-adjusted
  - **File:** `backend/ai_trading/features/momentum.py`
  - **Builds on:** `backend/orchestration/context_engineering/` — same feature computation
  - **Acceptance:** Momentum features plug into same feature registry; configurable lookback windows

- [ ] **5.4** Geometric Brownian motion: calibration, forecasting, confidence intervals
  - **File:** `backend/ai_trading/features/gbm.py`
  - **Builds on:** `backend/agents/volatility_agent/` — same volatility analysis
  - **Acceptance:** GBM helpers produce confidence intervals for forecasts; optional Black-Scholes reference

### C7.L3: Momentum Trading Model

- [ ] **5.5** Ranking engine: asset selection, holding period, rebalance schedule
  - **File:** `backend/ai_trading/strategies/momentum/model.py`
  - **Builds on:** `backend/agents/portfolio_agent/` — same portfolio construction
  - **Acceptance:** Ranking engine outputs portfolio allocations; confidence-filtered entries

- [ ] **5.6** Scenario simulation using Monte Carlo
  - **File:** `backend/ai_trading/strategies/momentum/scenario_sim.py`
  - **Builds on:** `backend/edge_lab/` — same Monte Carlo simulation engine
  - **Acceptance:** Scenario simulation reuses edge_lab Monte Carlo; configurable scenarios

### C7.L4: Momentum Backtest & Optimization

- [ ] **5.7** Momentum backtest analytics: Sharpe, max DD, turnover, hit ratio
  - **File:** `backend/ai_trading/strategies/momentum/backtest.py`
  - **Builds on:** `backend/ai_trading/backtest/engine.py` — same backtest engine
  - **Acceptance:** Momentum strategies run through same backtest engine; regime sensitivity

- [ ] **5.8** VaR and Expected Shortfall overlays
  - **File:** `backend/ai_trading/strategies/momentum/risk.py`
  - **Builds on:** `backend/ai_trading/finance/risks.py` — same risk analytics
  - **Acceptance:** VaR/ES compose existing risk calculations; configurable confidence levels

- [ ] **5.9** Momentum optimization: lookback windows, rebalance frequency, ranking thresholds
  - **File:** `backend/ai_trading/optimization/search.py`
  - **Builds on:** `backend/edge_lab/` — same Optuna hyperparameter search
  - **Acceptance:** Momentum optimization reuses existing search infrastructure; walk-forward-aware

### C7.L5: Momentum Reference Project

- [ ] **5.10** Flagship momentum strategy script
  - **File:** `backend/scripts/examples/ai_trading/05_momentum_trading.py`
  - **Builds on:** `backend/scripts/examples/agentic_ai/` — same example framework
  - **Acceptance:** Runnable: features → model → simulation → backtest → report; equity and FX examples

---

## Workstream 6 — Optimization & Production

### C6.L2: Regularization

- [ ] **6.1** Regularization controls: ridge/lasso, early stopping, tree depth limits
  - **File:** `backend/ai_trading/optimization/regularization.py`
  - **Builds on:** `backend/agents/runtime/output_validation.py` — same validation-with-repair pattern
  - **Acceptance:** Regularization controls integrated into ML training; configurable per model type

- [ ] **6.2** Bias/variance analysis and overfit flagging
  - **File:** `backend/ai_trading/optimization/stability.py`
  - **Builds on:** `backend/agents/runtime/circuit_breaker.py` — same state tracking
  - **Acceptance:** Overfit flags trigger same alerting patterns as circuit breakers; learning curves

### C6.L3: Hyperparameter Tuning

- [ ] **6.3** Grid, random, Bayesian optimization with time-series-aware CV
  - **File:** `backend/ai_trading/optimization/search.py`
  - **Builds on:** `backend/edge_lab/` — existing Optuna infrastructure
  - **Acceptance:** Hyperparameter search reuses edge_lab Optuna runners; parallel execution supported

### C6.L4: Strategy Optimization Loop

- [ ] **6.4** Promote/reject evaluation gate
  - **File:** `backend/ai_trading/optimization/robustness.py`
  - **Builds on:** `backend/services/approval/` — same ApprovalPacket pattern
  - **Acceptance:** Promotion uses same approval workflow with risk class A-E; OOS required

- [ ] **6.5** Robustness tests: shuffled order, slippage stress, data perturbation
  - **File:** `backend/ai_trading/optimization/robustness.py`
  - **Builds on:** `tests/chaos/` — same chaos testing patterns
  - **Acceptance:** Robustness tests follow same chaos testing methodology; stress reports generated

- [ ] **6.6** Feature importance and ablation workflow
  - **File:** `backend/ai_trading/optimization/feature_selection.py`
  - **Builds on:** `backend/orchestration/context_engineering/compression.py` — same feature analysis
  - **Acceptance:** Feature selection uses same context compression analysis; ablation reports

### C6.L5: Deployment & Production

- [ ] **6.7** Model registry: ID, training range, feature version, hyperparameters, status
  - **File:** `backend/ai_trading/optimization/registry.py`
  - **Builds on:** `backend/agents/runtime/schema_registry_service.py` — same registry pattern
  - **Acceptance:** Model registry follows same schema registry versioning; promotion status tracked

- [ ] **6.8** Drift monitoring: feature drift, prediction drift, live-vs-backtest divergence
  - **File:** `backend/ai_trading/optimization/drift_monitor.py`
  - **Builds on:** `backend/orchestration/context_engineering/contradiction.py` — same drift detection
  - **Acceptance:** Drift alerts use same contradiction resolver patterns; configurable thresholds

- [ ] **6.9** Production health alerts: latency, missing features, confidence collapse
  - **File:** `backend/ai_trading/optimization/drift_monitor.py`
  - **Builds on:** `backend/agents/runtime/circuit_breaker.py` — same alerting
  - **Acceptance:** Health alerts integrate with existing circuit breaker alerts; alert routing configurable

---

## Workstream 7 — Unified Reporting

- [ ] **7.1** Unified report builder: HTML/Markdown with standardized sections
  - **File:** `backend/ai_trading/reporting/report_builder.py`
  - **Builds on:** `backend/observability/` + `backend/agents/runtime/workflow_log.py`
  - **Acceptance:** Reports combine workflow logs, cost tracking, and finance analytics; exportable as HTML/Markdown/CSV

- [ ] **7.2** Strategy cards: dataset summary, features, training, predictive metrics, strategy metrics, risk metrics, caveats, verdict
  - **File:** `backend/ai_trading/reporting/strategy_cards.py`
  - **Builds on:** `backend/services/approval/` — same ApprovalPacket structure
  - **Acceptance:** Strategy cards are ApprovalPackets with finance analytics attached; standardized format

### Baseline Strategies

- [ ] **7.3** RSI baseline strategy
  - **File:** `backend/ai_trading/strategies/baselines/rsi.py`
  - **Builds on:** `backend/agents/monitoring_agent/` — same threshold-based signals
  - **Acceptance:** Produces same contract outputs (`TradeHypothesis`) as AI strategies

- [ ] **7.4** EMA cross baseline strategy
  - **File:** `backend/ai_trading/strategies/baselines/ema_cross.py`
  - **Builds on:** `backend/agents/regime_agent/` — same regime detection
  - **Acceptance:** Plugs into same backtest and reporting framework

- [ ] **7.5** Naive momentum baseline strategy
  - **File:** `backend/ai_trading/strategies/baselines/naive_momentum.py`
  - **Builds on:** `backend/agents/research_agent/` + `strategy_agent/` — same trend following
  - **Acceptance:** Comparable metrics output to AI-driven strategies

---

## Completion Summary

| Workstream | Tasks | Complete | Remaining |
|---|---|---|---|
| 1. Data Pipeline & Preprocessing | 6 | 0 | 6 |
| 2. ML Training | 8 | 0 | 8 |
| 3. Finance & Backtesting | 10 | 0 | 10 |
| 4. Reinforcement Learning | 11 | 0 | 11 |
| 5. Momentum Subsystem | 10 | 0 | 10 |
| 6. Optimization & Production | 9 | 0 | 9 |
| 7. Unified Reporting | 5 | 0 | 5 |
| **Total** | **59** | **0** | **59** |

**Already complete:** 18 lessons (no tasks needed)
**Grand total:** 34/34 lessons when all 59 tasks checked ✅

---

## Acceptance Gates (Every Task)

Each task above must pass:

- [ ] Code exists in `backend/ai_trading/` (reusable module, not just notebook)
- [ ] Unit tests exist (formula correctness, integration path coverage)
- [ ] Documentation exists (module README with usage examples)
- [ ] Traceability updated (lesson tag marked in this document)
- [ ] Example script or report artifact exists
- [ ] Reuses at least one existing HaruQuant component (agent, workflow, middleware, contract, MCP tool)

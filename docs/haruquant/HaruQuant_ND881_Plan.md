# HaruQuant ND881 Implementation Plan — Building on Existing Infrastructure

**Purpose:**
This document maps Udacity's **AI Trading Strategies Nanodegree (ND881)** onto the **existing HaruQuant codebase**. Every task builds on what is already implemented — agents, workflows, middleware, RAG, memory, MCP servers, contracts, observability — rather than starting from scratch. Nothing existing is removed; all prior work is the foundation.

**Program basis:** 8 courses, 34 lessons, 5 projects (updated March 26, 2026)

---

## 1. What Already Exists — ND881 Mapping

Before building anything new, this table shows which ND881 courses are **already covered** by existing HaruQuant components:

| ND881 Course | Lessons | Existing HaruQuant Coverage | Status |
|---|---|---|---|
| **C2: AI Workflows** | C2.L1–C2.L5 | 5 workflow patterns (sequential, routing, parallel, evaluator-optimizer, orchestrator-workers), DynamicOrchestratorWorkerRunner, async workflows | ✅ Complete |
| **C3.L1: ML Pipeline Overview** | C3.L1 | MiddlewarePipeline (5 layers), workflow execution log, workflow state persistence | ✅ Complete |
| **C3.L3: Feature Engineering** | C3.L3 | Context engineering (budget, compression, eviction, contradiction resolver), 68+ feature functions across edge_lab_outputs | ✅ Complete |
| **C6.L5: Deployment Considerations** | C6.L5 | Agent circuit breaker, cost enforcer, approval packets, compliance agent, risk governor | ✅ Complete |
| **C6.L1: Model Optimization** | C6.L1 | Edge lab optimization, hyperparameter search via Optuna, Monte Carlo simulation | ✅ Partial |
| **C8: Closeout** | C8.L1 | 10-phase workflow implementation plan (10/10), 258 tests, 38 companion docs | ✅ Complete |

**What needs to be built** (gaps):
- **C3.L2**: Data acquisition & preprocessing (ingestion pipelines, validation, normalization)
- **C3.L4/C3.L5**: EDA toolkit, data transformation projects
- **C4.L1–C4.L5**: Returns analytics, risk analytics, risk-adjusted ratios, portfolio backtesting, walk-forward validation
- **C5.L1–C5.L5**: Full RL subsystem (environment, state builder, action space, Q-learning, DQN, evaluator)
- **C6.L2–C6.4**: Regularization, hyperparameter tuning, strategy optimization, robustness suite, drift monitoring
- **C6.L6**: Classification optimization reference project
- **C7.L1–C7.5**: Momentum trading subsystem (statistical toolkit, features, model, backtest, flagship project)
- **Cross-cutting**: Unified reporting, ML model training (regression/classification), baseline strategies (RSI, EMA cross)

---

## 2. Reference Key

| Tag | Course |
|---|---|
| **C1** | Welcome to the Nanodegree |
| **C2** | Building a Workflow for AI |
| **C3** | Preparing for Data Analysis |
| **C4** | Evaluating Returns and Backtesting |
| **C5** | Reinforcement Learning |
| **C6** | Optimizing AI Strategies |
| **C7** | Momentum-Based Trading |
| **C8** | Congratulations |

---

## 3. Target Outcome

Build on the existing agentic foundation to add:
1. **Data pipelines** — ingestion, validation, preprocessing, feature registry
2. **Finance analytics** — returns, risk, drawdowns, Sharpe/Sortino/Calmar
3. **Backtesting engine** — portfolio, walk-forward, transaction costs
4. **ML training** — regression, classification with scikit-learn
5. **RL subsystem** — environment, Q-learning, DQN, evaluator
6. **Momentum strategies** — statistical toolkit, features, model, optimization
7. **Optimization suite** — regularization, hyperparameter search, robustness, drift monitoring
8. **Reporting** — unified strategy cards, HTML/Markdown reports
9. **5 reference projects** — data transformation, dynamic strategy, RL trading, classification optimization, momentum trading

All built **on top of** existing agents, workflows, middleware, RAG, memory, MCP tools, and observability.

---

## 4. Implementation Principles

1. **Reuse first** — Every existing agent, workflow pattern, middleware component, MCP server, contract, and memory store is reused. Nothing is replaced.
2. **Compose, don't duplicate** — New modules compose existing `ADKRunnerService`, `SequentialWorkflowRunner`, `ToolExecutor`, `RetrievalService`, `CostTracker`, etc.
3. **Research-to-production continuity** — Notebook experiments graduate into `backend/` library modules that plug into the same agentic runtime.
4. **Reproducibility** — Every model run, backtest, and optimization is reproducible from config + code version + dataset hash.
5. **Evaluation before promotion** — No strategy promoted to paper/live without OOS evaluation, walk-forward validation, risk analytics, and cost assumptions.

---

## 5. Repository Structure — Additions Only

The existing `backend/` structure stays. These directories are **added**:

```text
backend/
  # ← EVERYTHING HERE ALREADY EXISTS (agents, mcp, contracts, services, etc.)

  ai_trading/                    # NEW: ND881 trading subsystem
    data/
      ingestion.py               # C3.L2 — Data loaders (CSV, Parquet, yfinance)
      preprocessing.py           # C3.L2 — Missing values, outliers, session slicing
      validation.py              # C3.L2 — Schema validation, leakage-safe transforms
    features/
      momentum.py                # C7.L2 — Time-series, cross-sectional, volatility-adjusted momentum
      gbm.py                     # C7.L2 — Geometric Brownian motion calibration
    ml/
      datasets.py                # C3.L1 — Model-ready dataset builder
      regression.py              # C2.L3 — Linear, ridge/lasso, tree-based regressors
      classification.py          # C2.L4 — Logistic, decision tree, random forest
      calibration.py             # C2.L4 — Probability calibration, thresholding
      evaluation.py              # C2.L4 — Confusion matrix, ROC-AUC, precision/recall
    finance/
      returns.py                 # C4.L1 — Simple, log, cumulative, annualized, rolling returns
      risks.py                   # C4.L2 — Volatility, skew, kurtosis, exposure, concentration
      drawdowns.py               # C4.L3 — Max DD, avg DD, recovery duration
      ratios.py                  # C4.L3 — Sharpe, Sortino, Calmar, information ratio
    backtest/
      engine.py                  # C4.L4 — Event-driven backtest engine
      broker.py                  # C4.L4 — Simulated broker with fills, rejections
      position_sizer.py          # C4.L4 — Fixed, Kelly, vol-scaled, risk-parity sizing
      transaction_costs.py       # C4.L4 — Spread, commission, slippage modeling
      walk_forward.py            # C4.L4 — Anchaged/rolling window validation
      portfolio.py               # C4.L4 — Multi-asset portfolio backtesting
    rl/
      environment.py             # C5.L3 — Trading environment with broker constraints
      state_builder.py           # C5.L2 — Price windows, indicators, regime, PnL, risk budget
      action_space.py            # C5.L2 — Hold, enter/exit long/short, reduce, reverse
      reward_functions.py        # C5.L3 — PnL, Sharpe, drawdown-penalized, risk-adjusted
      q_learning.py              # C5.L3 — Tabular Q-learning agent
      dqn.py                     # C5.L3 — Deep Q-Network (optional)
      trainer.py                 # C5.L3 — Episode loop, replay buffer, checkpointing
      evaluator.py               # C5.L4 — OOS evaluation, reward comparison, stability
    optimization/
      regularization.py          # C6.L2 — Ridge/lasso, early stopping, tree depth limits
      search.py                  # C6.L3 — Grid, random, Bayesian optimization
      robustness.py              # C6.L4 — Shuffled order, slippage stress, data perturbation
      drift_monitor.py           # C6.L5 — Feature drift, prediction drift, live-vs-backtest
    strategies/
      baselines/                 # C2.L1 — RSI, EMA cross, naive momentum
      classification_alpha/      # C6.L6 — Classification model template project
      momentum/                  # C7.L3–C7.L5 — Momentum ranking engine, scenario simulation
    reporting/
      report_builder.py          # C8 — Unified HTML/Markdown report generation
      strategy_cards.py          # C8 — Standardized strategy evaluation cards
```

---

## 6. Master Workstreams

| # | Workstream | ND881 Courses | Builds On Existing |
|---|---|---|---|
| 1 | Data Pipeline & Preprocessing | C3.L2, C3.L4, C3.L5 | `backend/data/database/`, MCP servers, contracts |
| 2 | ML Training (Regression/Classification) | C2.L3, C2.L4, C6.L6 | `backend/agents/runtime/`, `backend/contracts/`, workflows |
| 3 | Finance Analytics & Backtesting | C4.L1–C4.L5 | `backend/agents/` risk_governor, portfolio agents, cost tracker |
| 4 | Reinforcement Learning | C5.L1–C5.L5 | `backend/agents/react/`, `backend/agents/runtime/workflows.py`, MCP tools |
| 5 | Momentum Subsystem | C7.L1–C7.L5 | `backend/retrieval/` (regime labels), memory, context engineering |
| 6 | Optimization & Production | C6.L2–C6.L5 | `backend/agents/runtime/circuit_breaker.py`, `backend/observability/`, edge_lab |
| 7 | Unified Reporting | All courses | `backend/observability/`, workflow logs, trajectory logs |

---

## 7. Detailed Implementation Plan

### Workstream 1 — Data Pipeline & Preprocessing

**C3.L2: Data Acquisition and Preprocessing**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| CSV/Parquet data loaders with canonical schema | `backend/ai_trading/data/ingestion.py` | `backend/data/database/repositories/` — same SQLite patterns | Ingest → validate → store in canonical format |
| Missing value, outlier, duplicate detection | `backend/ai_trading/data/preprocessing.py` | `backend/agents/runtime/middleware.py` — same pipeline pattern | Leakage-safe preprocessing with train/test separation |
| Market session slicing, timezone normalization | `backend/ai_trading/data/validation.py` | `backend/orchestration/context_engineering/` — same context awareness | Session markers applied to all OHLCV data |

**C3.L4: Exploratory Data Analysis**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Return distributions, rolling vol plots | `backend/ai_trading/reporting/report_builder.py` | `backend/observability/trace_model.py` — same structured logging | Reusable EDA routines for notebooks and reports |
| Cross-feature correlation heatmaps | `backend/ai_trading/reporting/report_builder.py` | `backend/orchestration/context_engineering/contradiction.py` — same correlation logic | Drift comparison views for temporal analysis |

**C3.L5: Data Transformation Reference Project**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| End-to-end ingestion → EDA → transformed dataset export | `backend/scripts/examples/ai_trading/01_data_transformation.py` | `backend/scripts/examples/agentic_ai/` — same example pattern | Runnable script that produces a report artifact |

---

### Workstream 2 — ML Training (Regression & Classification)

**C2.L3: Supervised Learning — Regression**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Target types: next-bar return, N-bar forward return, volatility forecast | `backend/ai_trading/ml/datasets.py` | `backend/contracts/observation_event.py` — same contract schema | Dataset builder produces labeled train/validate/test splits |
| Linear, ridge/lasso, tree-based regressors | `backend/ai_trading/ml/regression.py` | `backend/agents/runtime/litellm_runtime.py` — same model abstraction | Regressors trainable from config, comparable to baselines |
| Residual analysis, prediction-vs-actual diagnostics | `backend/ai_trading/ml/evaluation.py` | `backend/observability/cost_tracker.py` — same metrics tracking | Overfitting diagnostics with train/validation gap reporting |

**C2.L4: Supervised Learning — Classification**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Target types: up/down, multi-class, signal/no-signal | `backend/ai_trading/ml/datasets.py` | `backend/contracts/trade_hypothesis.py` — same contract-driven design | Classification targets derived from contract payloads |
| Logistic regression, decision tree, random forest | `backend/ai_trading/ml/classification.py` | `backend/agents/runtime/output_validation.py` — same validation pattern | Models produce probability outputs with calibration |
| Confusion matrix, ROC-AUC, precision/recall/F1 | `backend/ai_trading/ml/evaluation.py` | `backend/agents/runtime/workflow_log.py` — same structured logging | Evaluation report with all standard classification metrics |
| Probability calibration and thresholding | `backend/ai_trading/ml/calibration.py` | `backend/agents/prompts/` — same threshold-based decision patterns | Calibrated probabilities drive signal generation |

**C6.L6: Classification Optimization Reference Project**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| End-to-end: preprocessing → feature selection → tuning → evaluation → report | `backend/scripts/examples/ai_trading/02_classification_optimization.py` | `backend/scripts/examples/agentic_ai/02_agentic_workflows.py` — same multi-phase pattern | Runnable script producing strategy card report |

---

### Workstream 3 — Finance Analytics & Backtesting

**C4.L1: Measuring Returns**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Simple, log, cumulative, annualized, rolling returns | `backend/ai_trading/finance/returns.py` | `backend/contracts/execution_receipt.py` — same trade data schema | Returns engine produces all standard return metrics |
| Cumulative equity curve, rolling return windows | `backend/ai_trading/reporting/report_builder.py` | `backend/observability/` — same plotting infrastructure | Chart-ready return analytics |

**C4.L2: Measuring Risks**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Volatility, downside deviation, skewness, kurtosis | `backend/ai_trading/finance/risks.py` | `backend/agents/risk_governor_agent/` — same risk computation patterns | Risk analytics match risk_governor_agent outputs |
| Exposure metrics, concentration metrics | `backend/ai_trading/finance/risks.py` | `backend/agents/portfolio_agent/` — same portfolio exposure analysis | Trade-level and portfolio-level risk calculations |

**C4.L3: Risk-Adjusted Returns**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Drawdown series, max DD, recovery duration | `backend/ai_trading/finance/drawdowns.py` | `backend/agents/drawdown_agent/` — same drawdown analysis | Drawdown analytics match existing drawdown_agent outputs |
| Sharpe, Sortino, Calmar, information ratio | `backend/ai_trading/finance/ratios.py` | `backend/observability/cost_tracker.py` — same per-trace tracking | Risk-adjusted ratios per strategy and per trace |

**C4.L4: Backtesting Engine**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Event-driven backtest engine with simulated broker | `backend/ai_trading/backtest/engine.py`, `broker.py` | `backend/agents/execution_agent/` — same execution intent pattern | Backtest produces execution receipts matching live format |
| Position sizing: fixed, Kelly, vol-scaled, risk-parity | `backend/ai_trading/backtest/position_sizer.py` | `backend/agents/portfolio_agent/` — same portfolio math | Sizers plug into existing portfolio contracts |
| Transaction costs: spread, commission, slippage | `backend/ai_trading/backtest/transaction_costs.py` | `backend/observability/cost_tracker.py` — same cost tracking | Cost assumptions tracked and reported |
| Walk-forward validation: anchored/rolling windows | `backend/ai_trading/backtest/walk_forward.py` | `backend/agents/runtime/workflows.py` — same workflow pattern | Walk-forward as a workflow pattern composition |
| Multi-asset portfolio backtesting | `backend/ai_trading/backtest/portfolio.py` | `backend/orchestration/workflow/executor.py` — same execution model | Portfolio backtest produces same report format as single-asset |

**C4.L5: Dynamic Investment Strategy Reference Project**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Full project: dynamic allocation + measured risk + walk-forward + reporting | `backend/scripts/examples/ai_trading/03_dynamic_strategy.py` | `backend/scripts/examples/agentic_ai/` — same example framework | Runnable end-to-end strategy with report artifact |

---

### Workstream 4 — Reinforcement Learning

**C5.L1: RL Foundations**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| RL architecture doc — where RL fits relative to supervised/rule-based | `backend/ai_trading/rl/base.py` | `backend/agents/react/react_agent.py` — same agent loop pattern | RL documented as another agent type in the runtime |

**C5.L2: State and Action Space Design**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| State builder: price windows, indicators, regime, PnL, risk budget | `backend/ai_trading/rl/state_builder.py` | `backend/orchestration/context_engineering/` — same context composition | State composed from existing features + memory + regime labels |
| Action space: hold, enter/exit long/short, reduce, reverse | `backend/ai_trading/rl/action_space.py` | `backend/agents/execution_agent/` — same execution intent contracts | Actions mapped to `ExecutionIntent` contracts |
| Configurable action masks and constraints | `backend/ai_trading/rl/action_space.py` | `backend/agents/runtime/tool_policy.py` — same allowlist pattern | Action constraints enforced via same policy middleware |

**C5.L3: RL Trading Model Construction**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Trading environment with broker constraints, costs, reward calculation | `backend/ai_trading/rl/environment.py` | `backend/ai_trading/backtest/engine.py` — same backtest engine | Environment reuses backtest engine as the world simulator |
| Reward functions: PnL, Sharpe, drawdown-penalated | `backend/ai_trading/rl/reward_functions.py` | `backend/ai_trading/finance/ratios.py` — same Sharpe/Drawdown logic | Rewards compose existing finance analytics |
| Tabular Q-learning agent | `backend/ai_trading/rl/q_learning.py` | `backend/agents/react/react_agent.py` — same step loop | Q-learning as a specialized agent runtime |
| DQN (optional) | `backend/ai_trading/rl/dqn.py` | `backend/agents/runtime/litellm_runtime.py` — same model abstraction | DQN as alternative to tabular Q-learning |
| Training loop: episodes, replay buffer, checkpointing | `backend/ai_trading/rl/trainer.py` | `backend/agents/runtime/workflow_state.py` — same checkpoint persistence | Training checkpoints saved to same SQLite store |

**C5.L4: RL Evaluation**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| OOS evaluation, reward comparison, seed stability | `backend/ai_trading/rl/evaluator.py` | `backend/agents/runtime/workflow_log.py` — same execution logging | RL evaluator produces same report format as ML evaluator |
| Action frequency, turnover, cost sensitivity diagnostics | `backend/ai_trading/rl/evaluator.py` | `backend/observability/cost_tracker.py` — same per-action cost tracking | Cost-per-action breakdown in RL reports |

**C5.L5: RL Reference Project**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| End-to-end: train Q-learning agent → OOS evaluation → strategy report | `backend/scripts/examples/ai_trading/04_rl_trading.py` | `backend/scripts/examples/agentic_ai/` — same example framework | Runnable RL project with training curves and report |

---

### Workstream 5 — Momentum Subsystem

**C7.L1: Momentum Foundations**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Statistical helpers: Shapiro-Wilk, t-test, distribution summaries | `backend/ai_trading/strategies/momentum/stats.py` | `backend/orchestration/context_engineering/validator.py` — same validation patterns | Statistical tests for return significance |
| Momentum strategy taxonomy document | `docs/ai_trading/Momentum_Framework.md` | `docs/agentic_ai/` — same documentation patterns | Documented where momentum fits in strategy taxonomy |

**C7.L2: Momentum Features**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Time-series, cross-sectional, breakout, volatility-adjusted momentum | `backend/ai_trading/features/momentum.py` | `backend/orchestration/context_engineering/` — same feature computation | Momentum features plug into same feature registry |
| Geometric Brownian motion: calibration, forecasting, confidence intervals | `backend/ai_trading/features/gbm.py` | `backend/agents/volatility_agent/` — same volatility analysis | GBM helpers produce confidence intervals for forecasts |

**C7.L3: Momentum Trading Model**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Ranking engine: asset selection, holding period, rebalance schedule | `backend/ai_trading/strategies/momentum/model.py` | `backend/agents/portfolio_agent/` — same portfolio construction | Ranking engine outputs portfolio allocations |
| Confidence-filtered entries, scenario simulation | `backend/ai_trading/strategies/momentum/scenario_sim.py` | `backend/edge_lab/` — same Monte Carlo simulation | Scenario simulation reuses edge_lab Monte Carlo engine |

**C7.L4: Momentum Backtest & Optimization**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Momentum backtest analytics: Sharpe, max DD, turnover, hit ratio | `backend/ai_trading/strategies/momentum/backtest.py` | `backend/ai_trading/backtest/engine.py` — same backtest engine | Momentum strategies run through same backtest engine |
| VaR and Expected Shortfall overlays | `backend/ai_trading/strategies/momentum/risk.py` | `backend/ai_trading/finance/risks.py` — same risk analytics | VaR/ES compose existing risk calculations |
| Optimization: lookback windows, rebalance frequency, ranking thresholds | `backend/ai_trading/optimization/search.py` | `backend/edge_lab/` — same Optuna hyperparameter search | Momentum optimization reuses existing search infrastructure |

**C7.L5: Momentum Reference Project**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Flagship momentum strategy: features → model → simulation → backtest → report | `backend/scripts/examples/ai_trading/05_momentum_trading.py` | `backend/scripts/examples/agentic_ai/` — same example framework | Runnable flagship project with equity and FX examples |

---

### Workstream 6 — Optimization & Production

**C6.L2: Regularization**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Ridge/lasso, early stopping, tree depth limits | `backend/ai_trading/optimization/regularization.py` | `backend/agents/runtime/output_validation.py` — same validation-with-repair pattern | Regularization controls integrated into ML training |
| Bias/variance analysis, overfit flagging | `backend/ai_trading/optimization/stability.py` | `backend/agents/runtime/circuit_breaker.py` — same state tracking | Overfit flags trigger same alerting patterns as circuit breakers |

**C6.L3: Hyperparameter Tuning**

| Task | File | Builds On | Acceptance |
|---|---|---|
| Grid, random, Bayesian optimization with time-series-aware CV | `backend/ai_trading/optimization/search.py` | `backend/edge_lab/` — existing Optuna infrastructure | Hyperparameter search reuses edge_lab Optuna runners |
| Walk-forward-aware optimization | `backend/ai_trading/backtest/walk_forward.py` | `backend/agents/runtime/workflows.py` — same workflow patterns | Walk-forward as sequential workflow composition |

**C6.L4: Strategy Optimization Loop**

| Task | File | Builds On | Acceptance |
|---|---|---|
| Promote/reject evaluation gate | `backend/ai_trading/optimization/robustness.py` | `backend/services/approval/` — same ApprovalPacket pattern | Promotion uses same approval workflow with risk class A-E |
| Robustness tests: shuffled order, slippage stress, data perturbation | `backend/ai_trading/optimization/robustness.py` | `tests/chaos/` — same chaos testing patterns | Robustness tests follow same chaos testing methodology |
| Feature importance and ablation | `backend/ai_trading/optimization/feature_selection.py` | `backend/orchestration/context_engineering/compression.py` — same feature analysis | Feature selection uses same context compression analysis |

**C6.L5: Deployment & Production**

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Model registry: ID, training range, feature version, hyperparameters, status | `backend/ai_trading/optimization/registry.py` | `backend/agents/runtime/schema_registry_service.py` — same registry pattern | Model registry follows same schema registry versioning |
| Drift monitoring: feature drift, prediction drift, live-vs-backtest divergence | `backend/ai_trading/optimization/drift_monitor.py` | `backend/orchestration/context_engineering/contradiction.py` — same drift detection | Drift alerts use same contradiction resolver patterns |
| Production health alerts: latency, missing features, confidence collapse | `backend/ai_trading/optimization/drift_monitor.py` | `backend/agents/runtime/circuit_breaker.py` — same alerting | Health alerts integrate with existing circuit breaker alerts |

---

### Workstream 7 — Unified Reporting

| Task | File | Builds On | Acceptance |
|---|---|---|---|
| Unified report builder: HTML/Markdown with standardized sections | `backend/ai_trading/reporting/report_builder.py` | `backend/observability/` + `backend/agents/runtime/workflow_log.py` | Reports combine workflow logs, cost tracking, and finance analytics |
| Strategy cards: dataset summary, feature summary, training summary, predictive metrics, strategy metrics, risk metrics, caveats, verdict | `backend/ai_trading/reporting/strategy_cards.py` | `backend/services/approval/` — same ApprovalPacket structure | Strategy cards are ApprovalPackets with finance analytics attached |
| Baseline strategies: RSI, EMA cross, naive momentum | `backend/ai_trading/strategies/baselines/` | `backend/agents/` — same agent pattern | Baselines are agents with deterministic logic, produce same contract outputs |

---

## 8. Phase-Based Delivery Plan

| Phase | Workstreams | ND881 Courses | Deliverables | Existing Reused |
|---|---|---|---|---|
| **0** | Governance & skeleton | C1.L1 | Traceability register, module structure docs | Existing `docs/agentic_ai/` patterns |
| **1** | Data pipeline | C3.L2, C3.L4, C3.L5 | Ingestion, preprocessing, validation, EDA, reference project | `backend/data/database/`, MCP servers, contracts |
| **2** | ML training | C2.L3, C2.L4, C6.L6 | Regression, classification, calibration, evaluation, reference project | `backend/agents/runtime/`, workflows, contracts |
| **3** | Finance & backtesting | C4.L1–C4.L5 | Returns, risks, ratios, backtest engine, walk-forward, reference project | Risk/portfolio agents, cost tracker, observability |
| **4** | Reinforcement learning | C5.L1–C5.L5 | Environment, state/action, Q-learning, DQN, evaluator, reference project | ReAct agent, workflows, MCP tools, checkpoint persistence |
| **5** | Momentum | C7.L1–C7.L5 | Statistical toolkit, features, GBM, model, risk overlays, reference project | Edge lab Monte Carlo, regime labels, context engineering |
| **6** | Optimization & production | C6.L2–C6.L5 | Regularization, search, robustness, drift monitor, registry | Circuit breaker, approval packets, schema registry, chaos tests |
| **7** | Reporting & closeout | C8.L1 | Unified reports, strategy cards, baseline strategies, final audit | Workflow logs, cost tracker, ApprovalPacket, observability |

---

## 9. Baseline Strategies — Reusing Existing Agents

The existing 15 agents become the **baseline strategies** for ND881 comparison:

| Baseline Strategy | Existing Agent | ND881 Mapping |
|---|---|---|
| RSI strategy | `monitoring_agent` (threshold-based signals) | C2.L1 |
| EMA cross | `volatility_agent` + `regime_agent` (regime detection) | C2.L1 |
| Naive momentum | `research_agent` + `strategy_agent` (trend following) | C2.L1 |
| Risk parity portfolio | `portfolio_agent` + `risk_governor_agent` | C4.L4 |
| Compliance filter | `compliance_agent` | C6.L5 |
| Execution with slippage | `execution_agent` | C4.L4 |

These agents already produce structured contract outputs (`ObservationEvent`, `TradeHypothesis`, `EvaluationReport`) — the ML, RL, and momentum strategies produce the **same contract types** for apples-to-apples comparison.

---

## 10. Example Scripts — Building on Existing Patterns

New scripts follow the exact pattern of `backend/scripts/examples/agentic_ai/02_agentic_workflows.py`:

| Script | Content | Builds On |
|---|---|---|
| `01_data_transformation.py` | Ingest → preprocess → EDA → export | `02_agentic_workflows.py` example pattern |
| `02_classification_optimization.py` | Preprocess → feature selection → tuning → evaluate → report | `02_agentic_workflows.py` workflow composition |
| `03_dynamic_strategy.py` | Dynamic allocation + walk-forward + risk metrics | `SequentialWorkflowRunner` + finance analytics |
| `04_rl_trading.py` | Train Q-learning → OOS evaluation → report | `ReActAgentRuntime` + backtest engine |
| `05_momentum_trading.py` | Features → ranking → simulation → backtest → report | `EdgeLab` Monte Carlo + momentum features |

Each script:
1. Uses existing `ADKRunnerService` and `WorkflowExecutionLog`
2. Produces `WorkflowExecutionLog` with step records
3. Tracks costs via existing `CostTracker`
4. Outputs structured contracts (`TradeHypothesis`, `EvaluationReport`)
5. Runs without real LLM calls (mock agents for determinism)

---

## 11. Lesson-by-Lesson Coverage Matrix

| Lesson Tag | Lesson Title | HaruQuant Implementation | Builds On |
|---|---|---|---|
| C1.L1 | Welcome! | Governance, traceability register | Existing `docs/agentic_ai/` patterns |
| C2.L1 | AI Workflows in Trading | ✅ Already complete (5 workflow patterns) | `backend/agents/runtime/workflows.py` |
| C2.L2 | Unsupervised Learning | Regime detection | `backend/agents/regime_agent/`, `backend/orchestration/context_engineering/` |
| C2.L3 | Supervised: Regression | Regression module + evaluation | `backend/agents/runtime/`, contracts |
| C2.L4 | Supervised: Classification | Classification + calibration | `backend/agents/runtime/output_validation.py` |
| C2.L5 | Reinforcement Learning | ✅ Already complete (ReAct agent) | `backend/agents/react/react_agent.py` |
| C3.L1 | ML Pipeline Overview | ✅ Already complete (MiddlewarePipeline) | `backend/agents/runtime/middleware.py` |
| C3.L2 | Data Acquisition & Preprocessing | Ingestion, preprocessing, validation | `backend/data/database/` |
| C3.L3 | Feature Engineering | ✅ Already complete (context engineering) | `backend/orchestration/context_engineering/` |
| C3.L4 | Exploratory Data Analysis | EDA diagnostics, plotting, drift views | `backend/observability/` |
| C3.L5 | Project: Data Transformation | Reference script | `backend/scripts/examples/agentic_ai/` pattern |
| C4.L1 | Measuring Returns | Returns engine | `backend/contracts/execution_receipt.py` |
| C4.L2 | Measuring Risks | Risk engine | `backend/agents/risk_governor_agent/` |
| C4.L3 | Risk-Adjusted Returns | Drawdowns, ratios | `backend/agents/drawdown_agent/` |
| C4.L4 | Risk Parity Backtest | Portfolio backtest, walk-forward | `backend/agents/portfolio_agent/`, workflows |
| C4.L5 | Project: Dynamic Strategy | Reference script | `02_agentic_workflows.py` pattern |
| C5.L1 | RL in Trading | ✅ Already documented (ReAct) | `backend/agents/react/` |
| C5.L2 | State & Action Spaces | State builder, action space | `backend/orchestration/context_engineering/` |
| C5.L3 | RL Trading Model | Environment, Q-learning, DQN, trainer | `backend/agents/react/react_agent.py` |
| C5.L4 | RL Backtesting & Optimization | RL evaluator | `backend/agents/runtime/workflow_log.py` |
| C5.L5 | Project: RL Trading | Reference script | `02_agentic_workflows.py` pattern |
| C6.L1 | Model Optimization | ✅ Already complete (edge lab) | `backend/edge_lab/` |
| C6.L2 | Regularization | Regularization controls | `backend/agents/runtime/output_validation.py` |
| C6.L3 | Hyperparameter Tuning | Grid/random/Bayesian search | `backend/edge_lab/` Optuna |
| C6.L4 | Evaluating & Optimizing | Robustness suite, feature selection | `tests/chaos/`, `ApprovalPacket` |
| C6.L5 | Deployment Considerations | ✅ Already complete (circuit breaker, drift) | `backend/agents/runtime/circuit_breaker.py` |
| C6.L6 | Project: Classification Optimization | Reference script | `02_agentic_workflows.py` pattern |
| C7.L1 | Momentum-Based Trading | Statistical toolkit | `backend/orchestration/context_engineering/` |
| C7.L2 | Momentum Features | Momentum features, GBM | `backend/agents/volatility_agent/` |
| C7.L3 | Momentum Model | Ranking engine, scenario simulation | `backend/edge_lab/` Monte Carlo |
| C7.L4 | Momentum Backtesting | VaR, ES, optimization | `backend/ai_trading/backtest/engine.py` |
| C7.L5 | Project: Momentum Trading | Flagship reference script | `02_agentic_workflows.py` pattern |
| C8.L1 | Congratulations! | Final audit, readiness signoff | Existing `docs/agentic_ai/` patterns |

**Coverage summary:** 18/34 lessons already complete, 16/34 need new implementation.

---

## 12. Non-Negotiable Acceptance Gates

Every new module must pass:

1. **Code exists** — Reusable module in `backend/ai_trading/`, not just notebook
2. **Tests exist** — Unit tests for formulas, integration tests for pipelines
3. **Documentation exists** — Module README with usage examples
4. **Traceability updated** — Lesson tags marked complete in this document
5. **Example script exists** — Runnable script in `backend/scripts/examples/ai_trading/`
6. **Reuses existing infrastructure** — Composes existing agents, workflows, middleware, contracts, MCP tools — does not duplicate

---

## 13. Milestones

| Milestone | Courses | Deliverables | Weeks |
|---|---|---|---|
| **A — Data & ML Core** | C1, C2, C3 | Ingestion, preprocessing, regression, classification, EDA | 1–4 |
| **B — Finance & Backtest** | C4 | Returns, risks, ratios, backtest engine, walk-forward | 5–7 |
| **C — RL Subsystem** | C5 | Environment, Q-learning, evaluator, reference project | 8–11 |
| **D — Momentum & Optimization** | C6, C7 | Momentum features/model, regularization, search, robustness, drift | 12–14 |
| **E — Production & Closeout** | C8 | Unified reporting, baseline strategies, final audit | 15–16 |

---

## 14. Final Completion Definition

This plan is complete when:

- [ ] All 34 ND881 lessons marked covered (18 already done, 16 to implement)
- [ ] 5 reference scripts exist in `backend/scripts/examples/ai_trading/`
- [ ] All core subsystems modularized in `backend/ai_trading/`
- [ ] Every new module composes at least one existing HaruQuant component
- [ ] At least one strategy exists for each class:
  - Baseline/rule-based (existing agents)
  - Supervised regression (new ML module)
  - Supervised classification (new ML module)
  - Reinforcement learning (new RL module)
  - Momentum (new momentum module)
- [ ] Unified reporting combines workflow logs, cost tracking, and finance analytics
- [ ] Drift monitoring operational using existing circuit breaker + contradiction resolver patterns

---

## 15. Source Basis

Based on Udacity **AI Trading Strategies (ND881)** — 8 courses, 34 lessons, 5 projects, updated March 26, 2026.

All existing HaruQuant components referenced in this plan are verified present in the codebase at commit `HEAD`.

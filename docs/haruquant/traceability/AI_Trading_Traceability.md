# AI Trading Strategies Traceability Register

Status: canonical live status register
Scope: lesson coverage, workflow signoff, and global acceptance gates
Use this when: you need current implementation status or completion evidence
Companion docs: `../plans/ND881_Implementation_Plan.md`
Owner: program delivery
Review cadence: update with every implementation milestone or verification event

**Purpose:** Track course coverage from the source AI Trading Strategies plan to HaruQuant modules, workflows, tests, reports, and governance artifacts.

**Status key:** `not_started`, `in_progress`, `implemented`, `verified`, `accepted`

This is the canonical live status and signoff document for AI Trading
Strategies coverage in HaruQuant.

It supersedes earlier overlapping checklist and signoff documents that were
consolidated into this register.

## Foundation Status

- [x] Agent runtime foundation available in `agents/runtime/`
- [x] Canonical contracts available in `contracts/`
- [x] Domain service foundation available under `services/`
- [x] Operator and edge lab UI foundation available under `ui/src/app/(dashboard)/`
- [x] Test layers available under `tests/`

## Project Workflow Signoff

- [ ] `orchestration/workflow/definitions/data_transformation.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces dataset, EDA, feature, leakage, and evidence artifacts.
  - [x] Has integration test coverage.

- [ ] `orchestration/workflow/definitions/dynamic_strategy.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces returns, risk, walk-forward, cost, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `orchestration/workflow/definitions/rl_trading.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces checkpoint, OOS evaluation, action diagnostics, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `orchestration/workflow/definitions/classification_optimization.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces calibrated classifier, tuning, overfit, robustness, drift, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `orchestration/workflow/definitions/momentum_trading.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces momentum features, model, scenario, backtest, risk overlay, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

## Lesson Register

- [x] **C1.L1 - Program Foundation and Traceability**
  - **Status:** implemented
  - **Target modules:** `docs/haruquant/`, `orchestration/workflow/definitions/`
  - **Workflow:** all project workflow skeletons
  - **Tests:** workflow registry smoke validation for all five skeletons
  - **Artifacts:** traceability register, final coverage checklist, project workflow skeletons

- [x] **C2.L1 - Introduction to AI Workflows in Trading**
  - **Status:** implemented
  - **Target modules:** `orchestration/workflow/definitions/`, `services/strategy/baselines/`
  - **Workflow:** `classification_optimization.yaml`, `dynamic_strategy.yaml`, `momentum_trading.yaml`
  - **Tests:** `tests/unit/services/test_baseline_strategies.py`, `tests/integration/test_ai_trading_workflow_definitions.py`
  - **Artifacts:** RSI, EMA crossover, and naive momentum baseline modules; workflow skeletons

- [x] **C2.L2 - Unsupervised Learning**
  - **Status:** implemented
  - **Target modules:** `services/research/modeling/unsupervised.py`, `services/research/modeling/unsupervised_insights.py`
  - **Workflow:** `data_transformation.yaml` step `run_unsupervised_research`
  - **Example:** `scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py` examples 13-17
  - **Tests:** `tests/unit/services/test_unsupervised_modeling.py`, `tests/unit/services/test_unsupervised_insights.py`, `tests/integration/test_data_transformation_workflow.py`
  - **Artifacts:** unsupervised data summary, PCA metadata, K-Means cluster metadata, attachable regime labels, PCA risk factors, cluster outperformance report, cluster-adapted signal metadata

- [ ] **C2.L3 - Supervised Learning: Regression**
  - **Status:** not_started
  - **Target modules:** `services/research/modeling/datasets.py`, `services/research/modeling/regression.py`, `services/research/modeling/evaluation.py`
  - **Workflow:** `classification_optimization.yaml` or later regression workflow
  - **Tests:** regression target, training, and diagnostics tests
  - **Artifacts:** regression evaluation report

- [ ] **C2.L4 - Supervised Learning: Classification**
  - **Status:** not_started
  - **Target modules:** `services/research/modeling/classification.py`, `services/research/modeling/calibration.py`, `services/research/modeling/evaluation.py`
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** classifier, calibration, threshold, and metrics tests
  - **Artifacts:** classification strategy card

- [ ] **C2.L5 - Reinforcement Learning Introduction**
  - **Status:** not_started
  - **Target modules:** `services/rl/base.py`
  - **Workflow:** `rl_trading.yaml`
  - **Tests:** mock RL workflow bridge test
  - **Artifacts:** RL research-mode evaluation report

- [ ] **C3.L1 - ML Pipeline Overview**
  - **Status:** not_started
  - **Target modules:** `services/research/modeling/datasets.py`, `services/research/modeling/splits.py`
  - **Workflow:** `data_transformation.yaml`
  - **Tests:** dataset metadata and split tests
  - **Artifacts:** pipeline stage manifest

- [ ] **C3.L2 - Data Acquisition and Preprocessing**
  - **Status:** not_started
  - **Target modules:** `services/market_data/`, `services/research/data/`
  - **Workflow:** `data_transformation.yaml`
  - **Tests:** acquisition, validation, cleaning, and leakage tests
  - **Artifacts:** cleaned dataset and validation report

- [ ] **C3.L3 - Feature Engineering for Trading Models**
  - **Status:** not_started
  - **Target modules:** `services/data/features/`, `services/indicator/`, `services/research/features.py`
  - **Workflow:** `data_transformation.yaml`
  - **Tests:** feature formula and timestamp-alignment tests
  - **Artifacts:** feature manifest

- [ ] **C3.L4 - Exploratory Data Analysis**
  - **Status:** not_started
  - **Target modules:** `services/research/reporting.py`, `services/reporting/ai_trading_report_builder.py`
  - **Workflow:** `data_transformation.yaml`
  - **Tests:** EDA report payload tests
  - **Artifacts:** EDA report

- [ ] **C3.L5 - Data Transformation Project**
  - **Status:** not_started
  - **Target modules:** market data, research data, feature, evidence, and reporting services
  - **Workflow:** `data_transformation.yaml`
  - **Tests:** `tests/integration/test_data_transformation_workflow.py`
  - **Artifacts:** transformed dataset, feature manifest, EDA report, evidence manifest

- [ ] **C4.L1 - Measuring Returns**
  - **Status:** not_started
  - **Target modules:** `services/analytics/returns.py`, `services/analytics/benchmark.py`
  - **Workflow:** `dynamic_strategy.yaml`
  - **Tests:** return metric tests
  - **Artifacts:** return metrics report

- [ ] **C4.L2 - Measuring Risks**
  - **Status:** not_started
  - **Target modules:** `services/analytics/risks.py`, `services/risk/`
  - **Workflow:** `dynamic_strategy.yaml`
  - **Tests:** risk formula and service comparison tests
  - **Artifacts:** risk report

- [ ] **C4.L3 - Measuring Risk-Adjusted Returns**
  - **Status:** not_started
  - **Target modules:** `services/analytics/drawdowns.py`, `services/analytics/ratios.py`
  - **Workflow:** `dynamic_strategy.yaml`
  - **Tests:** drawdown and ratio tests
  - **Artifacts:** risk-adjusted metrics report

- [ ] **C4.L4 - Risk Parity Portfolio Backtesting**
  - **Status:** not_started
  - **Target modules:** `services/simulation/`, `services/optimization/walk_forward.py`
  - **Workflow:** `dynamic_strategy.yaml`
  - **Tests:** portfolio allocation and walk-forward tests
  - **Artifacts:** portfolio backtest report

- [ ] **C4.L5 - Dynamic Investment Strategy Project**
  - **Status:** not_started
  - **Target modules:** optimization, analytics, portfolio, evidence, and reporting services
  - **Workflow:** `dynamic_strategy.yaml`
  - **Tests:** `tests/integration/test_dynamic_strategy_workflow.py`
  - **Artifacts:** dynamic strategy card and evidence manifest

- [ ] **C5.L1 - RL in Trading**
  - **Status:** not_started
  - **Target modules:** `services/rl/base.py`
  - **Workflow:** `rl_trading.yaml`
  - **Tests:** RL base serialization tests
  - **Artifacts:** RL architecture metadata

- [ ] **C5.L2 - State and Action Spaces**
  - **Status:** not_started
  - **Target modules:** `services/rl/state_builder.py`, `services/rl/action_space.py`
  - **Workflow:** `rl_trading.yaml`
  - **Tests:** state shape and action mask tests
  - **Artifacts:** state/action manifest

- [ ] **C5.L3 - Reinforcement Trading Model**
  - **Status:** not_started
  - **Target modules:** `services/rl/environment.py`, `services/rl/reward_functions.py`, `services/rl/q_learning.py`, `services/rl/trainer.py`
  - **Workflow:** `rl_trading.yaml`
  - **Tests:** environment, reward, and Q-learning tests
  - **Artifacts:** training checkpoint and training curves

- [ ] **C5.L4 - RL Backtesting and Optimization**
  - **Status:** not_started
  - **Target modules:** `services/rl/evaluator.py`
  - **Workflow:** `rl_trading.yaml`
  - **Tests:** RL evaluator tests
  - **Artifacts:** OOS evaluation and action diagnostics

- [ ] **C5.L5 - RL Trading Project**
  - **Status:** not_started
  - **Target modules:** RL, simulation, analytics, evidence, and reporting services
  - **Workflow:** `rl_trading.yaml`
  - **Tests:** `tests/integration/test_rl_trading_workflow.py`
  - **Artifacts:** RL strategy card

- [ ] **C6.L1 - Model Optimization**
  - **Status:** not_started
  - **Target modules:** `services/optimization/scoring.py`, `services/optimization/models.py`
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** optimization objective tests
  - **Artifacts:** optimization objective manifest

- [ ] **C6.L2 - Regularization**
  - **Status:** not_started
  - **Target modules:** `services/research/modeling/regularization.py`, `services/research/modeling/evaluation.py`
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** regularization and overfit diagnostic tests
  - **Artifacts:** overfit diagnostics report

- [ ] **C6.L3 - Hyperparameter Tuning**
  - **Status:** not_started
  - **Target modules:** `services/optimization/methods/`, `services/optimization/execution.py`
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** bounded search integration tests
  - **Artifacts:** tuning result manifest

- [ ] **C6.L4 - Evaluating and Optimizing AI Strategies**
  - **Status:** not_started
  - **Target modules:** `services/optimization/robustness.py`, `services/optimization/feature_selection.py`
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** robustness and ablation tests
  - **Artifacts:** robustness report

- [ ] **C6.L5 - Deployment and Real-World Considerations**
  - **Status:** not_started
  - **Target modules:** `services/research/modeling/model_registry.py`, `services/research/modeling/drift.py`, `services/strategy/governance/`
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** model registry, drift, and promotion gate tests
  - **Artifacts:** model registry entry and shadow-readiness report

- [ ] **C6.L6 - Classification Optimization Project**
  - **Status:** not_started
  - **Target modules:** modeling, optimization, evidence, and reporting services
  - **Workflow:** `classification_optimization.yaml`
  - **Tests:** `tests/integration/test_classification_optimization_workflow.py`
  - **Artifacts:** classification strategy card

- [ ] **C7.L1 - Momentum Foundations**
  - **Status:** not_started
  - **Target modules:** `services/strategy/momentum/stats.py`
  - **Workflow:** `momentum_trading.yaml`
  - **Tests:** momentum statistical tests
  - **Artifacts:** momentum significance report

- [ ] **C7.L2 - Momentum Features**
  - **Status:** not_started
  - **Target modules:** `services/strategy/momentum/features.py`, `services/strategy/momentum/gbm.py`
  - **Workflow:** `momentum_trading.yaml`
  - **Tests:** momentum feature and GBM tests
  - **Artifacts:** momentum feature manifest

- [ ] **C7.L3 - Momentum Trading Model**
  - **Status:** not_started
  - **Target modules:** `services/strategy/momentum/model.py`, `services/strategy/momentum/scenario_sim.py`
  - **Workflow:** `momentum_trading.yaml`
  - **Tests:** ranking, rebalance, and scenario tests
  - **Artifacts:** momentum model manifest

- [ ] **C7.L4 - Momentum Backtesting and Optimization**
  - **Status:** not_started
  - **Target modules:** `services/strategy/momentum/backtest.py`, `services/strategy/momentum/risk.py`
  - **Workflow:** `momentum_trading.yaml`
  - **Tests:** momentum backtest and risk overlay tests
  - **Artifacts:** momentum backtest and risk report

- [ ] **C7.L5 - Momentum Trading Project**
  - **Status:** not_started
  - **Target modules:** momentum, optimization, analytics, evidence, and reporting services
  - **Workflow:** `momentum_trading.yaml`
  - **Tests:** `tests/integration/test_momentum_trading_workflow.py`
  - **Artifacts:** momentum strategy card

- [ ] **C8.L1 - Final Readiness Review**
  - **Status:** not_started
  - **Target modules:** `services/reporting/`, `services/execution/shadow/`, `services/strategy/governance/`, operator/edge UI
  - **Workflow:** all project workflows
  - **Tests:** targeted unit, integration, acceptance, eval, failure, and performance tests
  - **Artifacts:** final checklist and readiness evidence

## Global Acceptance Gates

- [ ] All implemented lessons have unit tests.
- [ ] All project workflows have integration tests.
- [ ] User-visible surfaces have acceptance tests where applicable.
- [ ] Promotion-bound strategies have risk, evidence, approval, shadow, and governance checks.
- [ ] Strategy cards are generated for baseline, supervised, RL, and momentum strategy classes.
- [ ] Operator UI can display workflow progress, evidence, approvals, incidents, and replay references.

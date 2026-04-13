# AI Trading Strategies Final Coverage Checklist

**Purpose:** Final signoff checklist for the AI Trading Strategies extension. A lesson or project should only be checked when code, workflow/API entrypoint, tests, evidence, reporting, and governance expectations are satisfied.

## Foundation

- [x] Agent runtime foundation is available.
- [x] Canonical contracts are available.
- [x] Domain services are available.
- [x] Operator, edge lab, and performance UI foundations are available.
- [x] Test layers are available.

## Project Workflows

- [ ] `backend/workflows/data_transformation.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces dataset, EDA, feature, leakage, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `backend/workflows/dynamic_strategy.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces returns, risk, walk-forward, cost, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `backend/workflows/rl_trading.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces checkpoint, OOS evaluation, action diagnostics, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `backend/workflows/classification_optimization.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces calibrated classifier, tuning, overfit, robustness, drift, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

- [ ] `backend/workflows/momentum_trading.yaml`
  - [x] Parses through the workflow definition parser.
  - [ ] Runs in dry-run/mock mode.
  - [ ] Produces momentum features, model, scenario, backtest, risk overlay, strategy card, and evidence artifacts.
  - [ ] Has integration test coverage.

## Lesson Signoff

- [x] C1.L1 - Program foundation and traceability
- [x] C2.L1 - AI workflows in trading
- [ ] C2.L2 - Unsupervised learning
- [ ] C2.L3 - Supervised learning: regression
- [ ] C2.L4 - Supervised learning: classification
- [ ] C2.L5 - Reinforcement learning introduction
- [ ] C3.L1 - ML pipeline overview
- [ ] C3.L2 - Data acquisition and preprocessing
- [ ] C3.L3 - Feature engineering
- [ ] C3.L4 - Exploratory data analysis
- [ ] C3.L5 - Data transformation project
- [ ] C4.L1 - Measuring returns
- [ ] C4.L2 - Measuring risks
- [ ] C4.L3 - Measuring risk-adjusted returns
- [ ] C4.L4 - Risk parity portfolio backtesting
- [ ] C4.L5 - Dynamic investment strategy project
- [ ] C5.L1 - RL in trading
- [ ] C5.L2 - State and action spaces
- [ ] C5.L3 - Reinforcement trading model
- [ ] C5.L4 - RL backtesting and optimization
- [ ] C5.L5 - RL trading project
- [ ] C6.L1 - Model optimization
- [ ] C6.L2 - Regularization
- [ ] C6.L3 - Hyperparameter tuning
- [ ] C6.L4 - Evaluating and optimizing AI strategies
- [ ] C6.L5 - Deployment and real-world considerations
- [ ] C6.L6 - Classification optimization project
- [ ] C7.L1 - Momentum foundations
- [ ] C7.L2 - Momentum features
- [ ] C7.L3 - Momentum trading model
- [ ] C7.L4 - Momentum backtesting and optimization
- [ ] C7.L5 - Momentum trading project
- [ ] C8.L1 - Final readiness review

## Global Gates

- [ ] All implemented lessons have unit tests.
- [ ] All project workflows have integration tests.
- [ ] User-visible surfaces have acceptance tests where applicable.
- [ ] Promotion-bound strategies have risk, evidence, approval, shadow, and governance checks.
- [ ] Strategy cards are generated for baseline, supervised, RL, and momentum strategy classes.
- [ ] Operator UI can display workflow progress, evidence, approvals, incidents, and replay references.

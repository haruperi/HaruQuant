# HaruQuant AI Trading Strategies Agentic Extension Checklist

**Purpose:** Convert the generic AI Trading Strategies implementation plan into a HaruQuant-native checklist. This plan keeps full coverage of the source curriculum while building on the agentic system already present in this repository: prompts, reasoning, planning, workflows, agents, MCP-style tool boundaries, canonical contracts, risk gates, approvals, evidence, audit/replay, shadow mode, operator UI, and tests.

**Source plan:** the existing generic AI Trading Strategies implementation plan in `docs/haruquant/`.
**Coverage retained:** 8 courses, the lesson tags enumerated in the source plan, and 5 project-grade workflows. The source plan states 34 lessons, while its explicit outline currently lists 33 lesson tags; the traceability register should preserve all listed tags and add the missing/renamed tag if it is later identified.

This is additive. Nothing existing is removed. New work should extend the closest existing HaruQuant namespace instead of creating isolated research-only modules.

---

## 0. Current HaruQuant Foundation

Use these existing systems as the base for every item:

- [x] **Agent runtime foundation**
  - **Target:** `backend/agents/runtime/`
  - **Existing foundation:** Middleware, prompt composition, retrieval guard, tool policy, output validation, circuit breaker, workflow logs, workflow state, async runners, dynamic orchestrator.
  - **Implementation rule:** Trading strategy workflows must use these runtime controls rather than bypassing them with standalone scripts.

- [x] **Canonical contract foundation**
  - **Target:** `backend/contracts/`
  - **Existing foundation:** `WorkflowIntent`, `WorkflowPlan`, `TradeHypothesis`, `TradeProposal`, `RiskAssessmentRequest`, `RiskAssessmentDecision`, `ExecutionIntent`, `ExecutionReceipt`, `ObservationEvent`, `EvaluationReport`, `ReplayBundle`.
  - **Implementation rule:** Prefer these contracts before introducing any new strategy-specific schema.

- [x] **Domain service foundation**
  - **Target:** `backend/services/market_data/`, `research/`, `features/`, `analytics/`, `optimization/`, `simulation/`, `risk/`, `risk_engine/`, `strategy/`, `strategy_gov/`, `approval/`, `evidence/`, `audit/`, `shadow/`
  - **Existing foundation:** Market data validation, research scorecards, leakage checks, analytics formulas, optimization search, simulation engine, risk gates, strategy lifecycle, evidence manifests, replay, and shadow mode.
  - **Implementation rule:** Extend these services rather than creating a separate `haruquant/` package.

- [x] **Operator/UI foundation**
  - **Target:** `ui/src/app/(dashboard)/operator/`, `ui/src/components/operator/`, `ui/src/app/(dashboard)/edge-lab/`, `ui/src/app/(dashboard)/performance/`
  - **Existing foundation:** Operator shell, workflows, evidence, approvals, replay, incidents, edge lab, performance pages.
  - **Implementation rule:** Show strategy workflow outputs through current operator/edge/performance surfaces where possible.

- [x] **Testing foundation**
  - **Target:** `tests/unit/`, `tests/integration/`, `tests/acceptance/`, `tests/eval/`, `tests/failure/`, `tests/perfomance/`
  - **Existing foundation:** Contract tests, backend integration tests, edge/risk acceptance tests, eval tasks, failure-path tests, performance tests.
  - **Implementation rule:** Add strategy workflow tests to these layers instead of creating an unrelated test hierarchy.

---

## 1. Course 1 - Welcome to the Nanodegree Program

### C1.L1 - Program Foundation and Traceability

- [x] **Create the AI trading strategy traceability register**
  - **Task:** Create a course/lesson register that tracks status, implementation path, workflow, tests, reports, evidence artifacts, and governance state.
  - **Target:** `docs/haruquant/AI_Trading_Strategies_Traceability_Register.md`
  - **Existing foundation:** Current HaruQuant docs, workflow catalog, agent catalog, policy map, benchmark/eval specs, contract tests.
  - **Acceptance:** Every source-plan lesson has an owner module, implementation status, test status, documentation status, artifact reference, and completion gate.
  - **Tests:** Manual docs review first; later add a docs validation script that checks all lesson tags appear in the register and final checklist.
  - **Usage example:**
    ```text
    C4.L3 -> backend/services/analytics/ratios.py
    Workflow -> dynamic_strategy.yaml
    Tests -> tests/unit/backend/services/test_ai_trading_ratios.py
    Artifact -> evidence://ai_trading/dynamic_strategy/latest
    Status -> in_progress
    ```

- [x] **Create the final coverage checklist**
  - **Task:** Add a signoff checklist for every enumerated lesson tag, any later-identified missing/renamed tag, and all 5 project workflows.
  - **Target:** `docs/haruquant/AI_Trading_Strategies_Final_Coverage_Checklist.md`
  - **Existing foundation:** Existing course checklist and implementation-plan docs under `docs/haruquant/`.
  - **Acceptance:** The checklist can be used to determine whether the source-plan coverage is fully implemented without reading source code.
  - **Tests:** Manual review until docs validation exists.
  - **Usage example:**
    ```text
    [ ] C5.L5 RL project workflow completed
        Evidence: replay bundle exists
        Tests: unit + integration + acceptance
        Promotion: shadow-only gate defined
    ```

- [x] **Create five project workflow skeletons**
  - **Task:** Add declarative workflow skeletons for the five project-grade workflows.
  - **Target:**
    - `backend/orchestration/workflow/definitions/data_transformation.yaml`
    - `backend/orchestration/workflow/definitions/dynamic_strategy.yaml`
    - `backend/orchestration/workflow/definitions/rl_trading.yaml`
    - `backend/orchestration/workflow/definitions/classification_optimization.yaml`
    - `backend/orchestration/workflow/definitions/momentum_trading.yaml`
  - **Existing foundation:** `backend/agents/runtime/workflow_definition.py`, workflow registry, workflow runners.
  - **Acceptance:** Each workflow parses, names required stages, declares contract outputs, and can run in dry-run/mock mode.
  - **Tests:** Workflow definition parser tests under `tests/unit/backend/agents/` or `tests/integration/backend/`.
  - **Usage example:**
    ```powershell
    pytest tests/unit/backend/agents/test_workflow_definition.py -q
    ```

---

## 2. Course 2 - Building a Workflow for AI

### C2.L1 - Introduction to AI Workflows in Trading

- [x] **Integrate AI trading experiments with HaruQuant workflows**
  - **Task:** Make trading strategy experiments execute as workflow stages instead of notebook-only or script-only flows.
  - **Target:** `backend/orchestration/workflow/definitions/*.yaml`, with helpers under `backend/services/modeling/`
  - **Existing foundation:** Sequential, parallel, routing, evaluator-optimizer, dynamic orchestrator, workflow logs, workflow state.
  - **Acceptance:** One workflow can run data prep, feature build, model fit, backtest, evaluation, evidence, and report assembly.
  - **Tests:** Integration test for at least one dry-run strategy workflow with mocked model training and mocked market data.
  - **Usage example:**
    ```python
    from backend.agents.runtime.workflow_definition import WorkflowRegistry

    registry = WorkflowRegistry()
    workflow = registry.get("classification_optimization")
    result = workflow.run(inputs={"symbol": "EURUSD", "timeframe": "H1"})
    ```

- [x] **Add RSI baseline strategy**
  - **Task:** Implement deterministic RSI signal generation that emits HaruQuant strategy outputs.
  - **Target:** `backend/services/strategy/baselines/rsi.py`
  - **Existing foundation:** `backend/services/strategy/base.py`, `adapter.py`, indicator modules, `TradeHypothesis`, `EvaluationReport`.
  - **Acceptance:** RSI signals run through the same evaluation and reporting path as ML strategies.
  - **Tests:** Unit tests for signal generation and thresholds; integration test for baseline -> backtest -> report.
  - **Usage example:**
    ```python
    strategy = RsiBaselineStrategy(period=14, oversold=30, overbought=70)
    signal = strategy.generate_signal(bars)
    ```

- [x] **Add EMA crossover baseline strategy**
  - **Task:** Implement fast/slow EMA crossover as a deterministic baseline.
  - **Target:** `backend/services/strategy/baselines/ema_cross.py`
  - **Existing foundation:** `backend/services/indicators/trend/ema.py`, strategy adapter, simulation service.
  - **Acceptance:** EMA cross produces reproducible signals and plugs into the same backtest adapter as RSI.
  - **Tests:** Unit tests for crossover detection; integration test for report generation.
  - **Usage example:**
    ```python
    strategy = EmaCrossBaselineStrategy(fast_period=12, slow_period=26)
    hypothesis = strategy.to_trade_hypothesis(symbol="EURUSD", bars=bars)
    ```

- [x] **Add naive momentum baseline strategy**
  - **Task:** Implement an N-period momentum baseline for comparison with advanced momentum work.
  - **Target:** `backend/services/strategy/baselines/naive_momentum.py`
  - **Existing foundation:** Research trend-persistence modules, analytics returns, strategy adapter.
  - **Acceptance:** Naive momentum can be compared against ML, RL, and advanced momentum strategy cards.
  - **Tests:** Unit tests for momentum calculation and signal direction; integration test through simulation/backtest.
  - **Usage example:**
    ```python
    strategy = NaiveMomentumStrategy(lookback=20, threshold=0.002)
    signal = strategy.generate_signal(bars)
    ```

### C2.L2 - Unsupervised Learning

- [x] **Add PCA and clustering model service**
  - **Task:** Implement PCA and clustering for regimes, factors, asset grouping, and feature-space partitioning.
  - **Target:** `backend/services/modeling/unsupervised.py`
  - **Existing foundation:** `backend/agents/regime_agent.py`, `backend/services/research/market_structure*.py`, feature pipeline.
  - **Acceptance:** Unsupervised labels can be attached to datasets and used by supervised models, RL state, and momentum filters.
  - **Tests:** Unit tests for deterministic labels with fixed seeds; integration test adding regime labels to a dataset.
  - **Usage example:**
    ```python
    result = cluster_feature_space(feature_frame, n_clusters=4, random_state=42)
    dataset = attach_cluster_labels(dataset, result, column_name="regime_label")
    ```

- [x] **Add unsupervised investment insight report**
  - **Task:** Explore investment data, summarize key stats, interpret PCA loadings as risk factors, score K-Means regimes by forward-return outperformance, and adapt strategy entry signals by cluster quality.
  - **Target:** `backend/services/modeling/unsupervised_insights.py`
  - **Existing foundation:** PCA/K-Means helpers, strategy baselines, workflow skeletons, strategy adapter, feature pipeline patterns.
  - **Acceptance:** A workflow stage can produce a single report containing EDA summary, PCA metadata, K-Means metadata, risk-factor loadings, cluster outperformance, and adapted signal metadata before supervised learning is introduced.
  - **Tests:** `tests/unit/backend/services/test_unsupervised_insights.py`
  - **Usage example:**
    ```python
    report = build_unsupervised_insight_report(
        feature_frame,
        feature_columns=["return_1", "return_3", "rolling_volatility", "range_pct"],
        signal_frame=signals,
        label_column="regime_label",
    )
    adapted = report.signal_adaptation.adapted_signals
    ```

### C2.L3 - Supervised Learning: Regression

- [ ] **Add regression dataset targets**
  - **Task:** Generate next-bar return, N-bar forward return, rolling horizon return, and volatility forecast targets.
  - **Target:** `backend/services/modeling/datasets.py`
  - **Existing foundation:** Research datasets, analytics returns, leakage checks.
  - **Acceptance:** Targets are leakage-safe and aligned with feature timestamps.
  - **Tests:** Unit tests for horizon alignment and no future leakage.
  - **Usage example:**
    ```python
    dataset = build_regression_dataset(bars, horizon=5, target="forward_return")
    ```

- [ ] **Add regression training service**
  - **Task:** Implement linear regression, ridge, lasso, and tree-based regressor baseline.
  - **Target:** `backend/services/modeling/regression.py`
  - **Existing foundation:** scikit-learn dependency, workflow logs, evidence artifacts.
  - **Acceptance:** Models train from config and emit metrics, model artifact reference, config hash, and data hash.
  - **Tests:** Unit tests with synthetic data; integration test through a workflow stage.
  - **Usage example:**
    ```python
    model, report = train_regression_model(dataset, model_type="ridge", alpha=1.0)
    ```

- [ ] **Add regression diagnostics**
  - **Task:** Add residual analysis, prediction-vs-actual, train/validation gap, and overfit flags.
  - **Target:** `backend/services/modeling/evaluation.py`
  - **Existing foundation:** `backend/services/analytics/metrics.py`, workflow logs, `EvaluationReport`.
  - **Acceptance:** Regression reports include predictive metrics and strategy-relevant caveats.
  - **Tests:** Unit tests for metric formulas; payload-shape tests for evaluation output.
  - **Usage example:**
    ```python
    evaluation = evaluate_regression_predictions(y_true, y_pred, split="validation")
    ```

### C2.L4 - Supervised Learning: Classification

- [ ] **Add classification dataset targets**
  - **Task:** Generate up/down, multi-class return bucket, signal/no-signal, and regime class targets.
  - **Target:** `backend/services/modeling/datasets.py`
  - **Existing foundation:** Research classifier, feature pipeline, leakage checks.
  - **Acceptance:** Labels are time-aligned, class distributions are reported, and label metadata is stored.
  - **Tests:** Unit tests for label generation and class-balance summaries.
  - **Usage example:**
    ```python
    dataset = build_classification_dataset(bars, horizon=3, target="direction")
    ```

- [ ] **Add classification training service**
  - **Task:** Implement logistic regression, decision tree, random forest, and optional gradient-boosted baseline.
  - **Target:** `backend/services/modeling/classification.py`
  - **Existing foundation:** `backend/services/research/classifier.py`, output validation, workflow logs.
  - **Acceptance:** Classifiers output calibrated probabilities and thresholdable signals.
  - **Tests:** Unit tests on synthetic separable data; integration test through classification optimization workflow.
  - **Usage example:**
    ```python
    model, report = train_classifier(dataset, model_type="random_forest")
    probabilities = model.predict_proba(dataset.x_test)
    ```

- [ ] **Add calibration and thresholding**
  - **Task:** Add probability calibration, threshold selection, and signal/no-signal conversion.
  - **Target:** `backend/services/modeling/calibration.py`
  - **Existing foundation:** Policy threshold patterns, output validation, `EvaluationReport`.
  - **Acceptance:** Strategy signals are generated from probabilities using declared thresholds and calibration metadata.
  - **Tests:** Unit tests for threshold conversion and calibration payloads.
  - **Usage example:**
    ```python
    threshold = choose_threshold(y_valid, p_valid, objective="f1")
    signals = probabilities_to_signals(p_test, threshold=threshold)
    ```

- [ ] **Add classification metrics**
  - **Task:** Add confusion matrix, precision, recall, F1, ROC-AUC, and class-balance diagnostics.
  - **Target:** `backend/services/modeling/evaluation.py`
  - **Existing foundation:** `backend/contracts/evaluation_report/`, analytics metrics.
  - **Acceptance:** Classification metrics appear in strategy cards and evaluation reports.
  - **Tests:** Unit tests against scikit-learn expected outputs.
  - **Usage example:**
    ```python
    evaluation = evaluate_classifier(y_true, y_pred, y_proba)
    ```

### C2.L5 - Reinforcement Learning Introduction

- [ ] **Add RL workflow bridge**
  - **Task:** Allow RL experiments to launch from the same workflow surface as supervised and baseline strategies.
  - **Target:** `backend/services/rl/base.py`, `backend/orchestration/workflow/definitions/rl_trading.yaml`
  - **Existing foundation:** `backend/agents/react/`, workflow state, dynamic orchestrator, simulation service.
  - **Acceptance:** RL can run in research mode without live side effects and emit an `EvaluationReport`.
  - **Tests:** Integration test for mock RL trainer -> evaluator -> report.
  - **Usage example:**
    ```python
    result = run_rl_experiment(config, mode="research")
    assert result.evaluation.verdict in {"PASS", "WARN", "FAIL"}
    ```

---

## 3. Course 3 - Preparing for Data Analysis

### C3.L1 - ML Pipeline Overview

- [ ] **Formalize ML pipeline stage contracts**
  - **Task:** Define reusable dataset and split objects for ingest, validate, preprocess, feature, label, split, train, evaluate, backtest, export.
  - **Target:** `backend/services/modeling/datasets.py`, `backend/services/modeling/splits.py`
  - **Existing foundation:** Runtime middleware, workflow logs, schema registry service.
  - **Acceptance:** Pipeline stages are explicit and can be recorded in workflow logs and evidence manifests.
  - **Tests:** Unit tests for dataset metadata and split boundaries.
  - **Usage example:**
    ```python
    train, valid, test = make_time_series_splits(dataset, train_size=0.6, valid_size=0.2)
    ```

### C3.L2 - Data Acquisition and Preprocessing

- [ ] **Extend data acquisition**
  - **Task:** Support CSV, Parquet, Dukascopy bars/ticks, and broker-exported data under one canonical schema.
  - **Target:** `backend/services/market_data/data_getters.py`, `backend/services/market_data/dukascopy.py`, new adapters if needed.
  - **Existing foundation:** Market data getters, Dukascopy integration, validators.
  - **Acceptance:** Data loads with symbol, timestamp, OHLCV, spread, source, and timezone metadata.
  - **Tests:** Unit tests using CSV/Parquet fixtures; integration test for canonical schema validation.
  - **Usage example:**
    ```python
    bars = load_market_data(source="csv", path="data/EURUSD_H1.csv", symbol="EURUSD")
    ```

- [ ] **Extend data validation**
  - **Task:** Detect missing segments, duplicate timestamps, malformed OHLC values, stale prices, spread anomalies, and timezone issues.
  - **Target:** `backend/services/market_data/data_validator.py`, `backend/services/research/data/validation.py`
  - **Existing foundation:** Existing data validator and research data validation.
  - **Acceptance:** Validation returns structured findings and severity levels; severe findings block training unless explicitly overridden in research mode.
  - **Tests:** Unit tests for each validation rule using small fixtures.
  - **Usage example:**
    ```python
    validation = validate_market_frame(bars)
    assert validation.severity != "BLOCKER"
    ```

- [ ] **Extend preprocessing**
  - **Task:** Add missing-value handling, outlier tags, session slicing, timezone normalization, train-only scaling, and transform replay.
  - **Target:** `backend/services/research/data/cleaning.py`, `backend/services/market_data/data_manipulator.py`
  - **Existing foundation:** Research data cleaning and market data manipulation.
  - **Acceptance:** Preprocessing is reproducible and stores fitted transform metadata only from training data.
  - **Tests:** Unit tests for no leakage, deterministic transforms, and session filters.
  - **Usage example:**
    ```python
    cleaned, transform_manifest = preprocess_market_data(bars, fit_range=("2020-01-01", "2023-01-01"))
    ```

### C3.L3 - Feature Engineering for Trading Models

- [ ] **Expand technical and statistical features**
  - **Task:** Add returns, log returns, volatility, ATR/ADR, RSI, Williams %R, MACD, EMA spreads, z-scores, skew, kurtosis.
  - **Target:** `backend/services/features/pipeline.py`, `backend/services/indicators/*`, `backend/services/research/features.py`
  - **Existing foundation:** Indicator modules, feature pipeline, research features.
  - **Acceptance:** Features declare lookback, lag, leakage status, source, and owner.
  - **Tests:** Unit tests for formula correctness and timestamp alignment.
  - **Usage example:**
    ```python
    features = build_feature_frame(bars, feature_set="ai_trading_core")
    ```

- [ ] **Add context and structure features**
  - **Task:** Add candle body/range, gaps, session indicators, regime labels, and cross-symbol relative strength.
  - **Target:** `backend/services/features/pipeline.py`, `backend/services/modeling/unsupervised.py`
  - **Existing foundation:** Regime agent, market structure research, feature pipeline.
  - **Acceptance:** Context features can be included in supervised, RL, and momentum datasets.
  - **Tests:** Unit tests for feature availability and no future data leakage.
  - **Usage example:**
    ```python
    features = build_feature_frame(bars, feature_set="ai_trading_context")
    ```

### C3.L4 - Exploratory Data Analysis

- [ ] **Add EDA report sections**
  - **Task:** Add return distributions, missingness, rolling volatility, correlation heatmaps, target-feature relationships, regime segmentation, and temporal drift.
  - **Target:** `backend/services/research/reporting.py`, `backend/services/research/profile_reporting.py`, `backend/services/reporting/ai_trading_report_builder.py`
  - **Existing foundation:** Research reporting, scorecards, profile snapshots, edge lab UI.
  - **Acceptance:** EDA output can render as Markdown/HTML and attach to evidence manifests.
  - **Tests:** Unit tests for report section payload shape; integration test for data transformation workflow report.
  - **Usage example:**
    ```python
    report = build_eda_report(dataset, sections=["missingness", "distributions", "drift"])
    ```

### C3.L5 - Project: Data Transformation for Trading Models

- [ ] **Implement the data transformation workflow**
  - **Task:** Build ingest -> validate -> preprocess -> feature -> EDA -> transformed export -> evidence.
  - **Target:** `backend/orchestration/workflow/definitions/data_transformation.yaml`
  - **Existing foundation:** Market data service, research data validation, feature leakage checks, evidence storage.
  - **Acceptance:** Workflow produces a transformed dataset, EDA report, feature manifest, and evidence manifest.
  - **Tests:** Integration test with fixture data and deterministic output hashes.
  - **Usage example:**
    ```powershell
    pytest tests/integration/backend/test_data_transformation_workflow.py -q
    ```

---

## 4. Course 4 - Evaluating Returns and Backtesting

### C4.L1 - Measuring Returns

- [ ] **Harden returns analytics**
  - **Task:** Ensure simple, log, cumulative, annualized, rolling, and benchmark-relative returns are reusable and tested.
  - **Target:** `backend/services/analytics/returns.py`, `backend/services/analytics/benchmark.py`
  - **Existing foundation:** Current analytics modules and performance UI expectations.
  - **Acceptance:** Return metrics are available to reports, backtests, strategy cards, and promotion evidence.
  - **Tests:** Unit tests with fixed expected numerical values.
  - **Usage example:**
    ```python
    metrics = calculate_return_metrics(equity_curve, benchmark=benchmark_curve)
    ```

### C4.L2 - Measuring Risks

- [ ] **Harden risk analytics**
  - **Task:** Add or verify volatility, downside deviation, skewness, kurtosis, exposure, concentration, and holding-period distributions.
  - **Target:** `backend/services/analytics/risks.py`, `backend/services/analytics/distributions.py`, `backend/services/risk/*`
  - **Existing foundation:** Risk engine, risk governor, analytics risk modules.
  - **Acceptance:** Same metrics can be used in research reports and risk governance gates.
  - **Tests:** Unit tests for formulas; integration test comparing strategy card risk summary with risk service output.
  - **Usage example:**
    ```python
    risk = calculate_strategy_risk(trades, equity_curve, positions)
    ```

### C4.L3 - Measuring Risk-Adjusted Returns

- [ ] **Harden drawdown analytics**
  - **Task:** Add drawdown series, max drawdown, average drawdown, drawdown duration, and recovery duration.
  - **Target:** `backend/services/analytics/drawdowns.py`
  - **Existing foundation:** Drawdown agent and analytics module.
  - **Acceptance:** Drawdown outputs are consistent across performance UI, strategy cards, and risk gates.
  - **Tests:** Unit tests with fixed equity curves.
  - **Usage example:**
    ```python
    drawdowns = calculate_drawdown_metrics(equity_curve)
    ```

- [ ] **Harden ratio analytics**
  - **Task:** Add Sharpe, Sortino, Calmar, information ratio, and recovery factor.
  - **Target:** `backend/services/analytics/ratios.py`, `backend/services/analytics/efficiency.py`
  - **Existing foundation:** Analytics ratio and efficiency modules.
  - **Acceptance:** Ratios support all/long/short splits where trade data is available.
  - **Tests:** Unit tests against known values and edge cases such as zero volatility.
  - **Usage example:**
    ```python
    ratios = calculate_risk_adjusted_ratios(returns, drawdowns, benchmark_returns)
    ```

### C4.L4 - Backtesting a Risk Parity Portfolio

- [ ] **Add backtest adapter layer**
  - **Task:** Connect strategy outputs to simulation/backtest execution-like events and receipts.
  - **Target:** `backend/services/simulation/`, `backend/services/strategy/adapter.py`
  - **Existing foundation:** Simulation engine, execution receipt contract, execution service semantics.
  - **Acceptance:** Offline backtests emit records comparable to shadow, paper, and live paths.
  - **Tests:** Integration test: strategy signal -> simulated order -> execution receipt -> report.
  - **Usage example:**
    ```python
    backtest = run_strategy_backtest(strategy, bars, initial_equity=100000)
    ```

- [ ] **Add portfolio and risk-parity backtest support**
  - **Task:** Implement equal weight, vol-scaled, constrained, and risk-parity approximation portfolio backtests.
  - **Target:** `backend/services/optimization/walk_forward.py`, simulation portfolio adapter.
  - **Existing foundation:** Portfolio agent, risk engine, optimization walk-forward module.
  - **Acceptance:** Portfolio backtests support anchored and rolling walk-forward windows.
  - **Tests:** Unit tests for allocation weights; integration test for walk-forward portfolio run.
  - **Usage example:**
    ```python
    result = run_portfolio_backtest(symbols, allocation="risk_parity", rebalance="monthly")
    ```

- [ ] **Add transaction cost modeling**
  - **Task:** Model spread, commission, slippage, and swap placeholders.
  - **Target:** Simulation/backtest cost adapter, `backend/config/cost/routing_policy.yaml`
  - **Existing foundation:** Slippage agent, execution service, cost config, observability cost tracking.
  - **Acceptance:** Costs are included in every backtest report and evidence manifest.
  - **Tests:** Unit tests for cost calculations; integration test comparing gross vs net performance.
  - **Usage example:**
    ```python
    result = run_strategy_backtest(strategy, bars, costs={"spread": 0.8, "commission": 7.0})
    ```

### C4.L5 - Project: Evaluating and Backtesting a Dynamic Investment Strategy

- [ ] **Implement dynamic strategy workflow**
  - **Task:** Build a full dynamic allocation workflow with measured risk, walk-forward validation, cost assumptions, report, and promotion verdict.
  - **Target:** `backend/orchestration/workflow/definitions/dynamic_strategy.yaml`
  - **Existing foundation:** Optimization, analytics, portfolio agent, risk engine, evidence service.
  - **Acceptance:** Workflow produces a strategy card and is eligible only for shadow review unless governance gates pass.
  - **Tests:** Integration test for dynamic strategy workflow; acceptance test for strategy card/evidence output.
  - **Usage example:**
    ```powershell
    pytest tests/integration/backend/test_dynamic_strategy_workflow.py -q
    ```

---

## 5. Course 5 - Reinforcement Learning

### C5.L1 - Reinforcement Learning in Trading

- [ ] **Add RL architecture and base abstractions**
  - **Task:** Define environment, state, action, reward, episode, policy, exploration, and evaluation interfaces.
  - **Target:** `backend/services/rl/base.py`
  - **Existing foundation:** ReAct agent loop, workflow law, simulation service, contract validation.
  - **Acceptance:** RL is represented as deterministic service logic plus workflow orchestration, not as ungated live action.
  - **Tests:** Unit tests for base dataclasses/interfaces and serialization.
  - **Usage example:**
    ```python
    episode = RlEpisode(id="eurusd-h1-2024-w01", seed=42)
    ```

### C5.L2 - Representing the Financial Market: State and Action Spaces

- [ ] **Add RL state builder**
  - **Task:** Build state vectors from price windows, indicators, volatility, regime, open position, unrealized PnL, and risk budget.
  - **Target:** `backend/services/rl/state_builder.py`
  - **Existing foundation:** Feature pipeline, regime agent, risk services, portfolio state.
  - **Acceptance:** State definitions are versioned and reproducible.
  - **Tests:** Unit tests for shape, feature ordering, missing-feature behavior, and deterministic output.
  - **Usage example:**
    ```python
    state = build_rl_state(bars, features, position_state, risk_budget)
    ```

- [ ] **Add RL action space and masks**
  - **Task:** Implement hold, enter long, enter short, exit, reduce, reverse, and allocation bucket actions with policy-aware masks.
  - **Target:** `backend/services/rl/action_space.py`
  - **Existing foundation:** `ExecutionIntent`, tool policy, risk restrictions, operating envelopes.
  - **Acceptance:** Invalid or unsafe actions are masked before training/evaluation output can become a proposal.
  - **Tests:** Unit tests for masks under flat, long, short, risk-blocked, and kill-switch states.
  - **Usage example:**
    ```python
    allowed_actions = action_space.mask(state, policy_context)
    ```

### C5.L3 - Constructing a Reinforcement Trading Model

- [ ] **Add RL trading environment**
  - **Task:** Build an episodic trading environment over historical data with broker constraints, costs, reward calculation, and position transitions.
  - **Target:** `backend/services/rl/environment.py`
  - **Existing foundation:** Simulation engine, transaction cost model, execution semantics.
  - **Acceptance:** Environment emits replayable observations and does not perform live side effects.
  - **Tests:** Unit tests for reset/step behavior; integration test for one complete episode.
  - **Usage example:**
    ```python
    env = TradingEnvironment(bars, cost_model=cost_model)
    state = env.reset(seed=42)
    next_state, reward, done, info = env.step(action)
    ```

- [ ] **Add reward functions**
  - **Task:** Implement PnL, Sharpe-like, drawdown-penalized, turnover-penalized, and risk-adjusted rewards.
  - **Target:** `backend/services/rl/reward_functions.py`
  - **Existing foundation:** Analytics returns, ratios, drawdowns, costs.
  - **Acceptance:** Reward functions are deterministic and documented in model evidence.
  - **Tests:** Unit tests for each reward function using fixed transitions.
  - **Usage example:**
    ```python
    reward = drawdown_penalized_reward(previous_state, next_state, trade_cost)
    ```

- [ ] **Add Q-learning trainer**
  - **Task:** Implement tabular Q-learning with epsilon-greedy exploration, checkpointing, and episode summaries.
  - **Target:** `backend/services/rl/q_learning.py`, `backend/services/rl/trainer.py`
  - **Existing foundation:** Workflow state persistence, evidence storage.
  - **Acceptance:** Training is reproducible by seed and creates checkpoints and training curves.
  - **Tests:** Unit test convergence on a tiny deterministic environment; integration test for saved checkpoint.
  - **Usage example:**
    ```python
    trainer = QLearningTrainer(env, alpha=0.1, gamma=0.95, epsilon=0.2)
    result = trainer.train(episodes=100, seed=42)
    ```

- [ ] **Add optional DQN trainer**
  - **Task:** Add a DQN baseline if dependency and runtime constraints are acceptable.
  - **Target:** `backend/services/rl/dqn.py`
  - **Existing foundation:** Model registry and evidence artifacts.
  - **Acceptance:** DQN is optional and never blocks Q-learning project completion.
  - **Tests:** Smoke test with tiny network/config if implemented.
  - **Usage example:**
    ```python
    result = train_dqn(env, config=dqn_config)
    ```

### C5.L4 - Backtesting and Optimization Techniques

- [ ] **Add RL evaluator**
  - **Task:** Evaluate OOS reward, PnL, drawdown, Sharpe, turnover, action frequency, costs, reward comparison, and seed stability.
  - **Target:** `backend/services/rl/evaluator.py`
  - **Existing foundation:** `EvaluationReport` contract, analytics modules, trajectory evals.
  - **Acceptance:** RL evaluation produces the same strategy card format as other strategy classes.
  - **Tests:** Unit tests for evaluator summaries; integration test for train -> evaluate -> report.
  - **Usage example:**
    ```python
    evaluation = evaluate_rl_policy(policy, oos_env, seeds=[1, 2, 3, 4, 5])
    ```

### C5.L5 - Project: Building a Reinforcement Learning Trading Model

- [ ] **Implement RL project workflow**
  - **Task:** Build train -> OOS evaluate -> backtest -> evidence -> strategy card workflow.
  - **Target:** `backend/orchestration/workflow/definitions/rl_trading.yaml`
  - **Existing foundation:** RL service, simulation, analytics, evidence, workflow runtime.
  - **Acceptance:** Workflow produces checkpoints, curves, OOS metrics, action diagnostics, and a shadow-only promotion verdict.
  - **Tests:** Integration test with a small fixture dataset and deterministic seed.
  - **Usage example:**
    ```powershell
    pytest tests/integration/backend/test_rl_trading_workflow.py -q
    ```

---

## 6. Course 6 - Optimizing AI Strategies

### C6.L1 - Introduction to AI Model Optimization

- [ ] **Standardize optimization objectives**
  - **Task:** Define predictive, trading, risk-adjusted, and multi-objective optimization scores.
  - **Target:** `backend/services/optimization/scoring.py`, `backend/services/optimization/models.py`
  - **Existing foundation:** Existing optimization core and scoring.
  - **Acceptance:** Objectives can be used by supervised, RL, momentum, and dynamic strategy workflows.
  - **Tests:** Unit tests for score composition and weight handling.
  - **Usage example:**
    ```python
    score = score_candidate(metrics, objective="risk_adjusted_return")
    ```

### C6.L2 - Regularization Techniques to Prevent Overfitting

- [ ] **Add regularization controls**
  - **Task:** Support ridge/lasso, early stopping, tree depth, min leaf, and complexity settings.
  - **Target:** `backend/services/modeling/regularization.py`
  - **Existing foundation:** scikit-learn dependency, modeling service, optimization config.
  - **Acceptance:** Regularization settings are captured in model artifact metadata and strategy cards.
  - **Tests:** Unit tests for config translation into estimator parameters.
  - **Usage example:**
    ```python
    estimator = apply_regularization(base_estimator, RegularizationConfig(kind="lasso", alpha=0.01))
    ```

- [ ] **Add overfit diagnostics**
  - **Task:** Add train-vs-validation gap, learning curves, bias/variance flags, and model complexity flags.
  - **Target:** `backend/services/modeling/evaluation.py`
  - **Existing foundation:** Workflow logs, analytics metrics, `EvaluationReport`.
  - **Acceptance:** Overfit findings are visible in reports and can block promotion.
  - **Tests:** Unit tests with synthetic overfit/underfit examples.
  - **Usage example:**
    ```python
    overfit = detect_overfit(train_metrics, valid_metrics, thresholds=config.thresholds)
    ```

### C6.L3 - Hyperparameter Tuning Methods

- [ ] **Extend time-series-aware search**
  - **Task:** Add time-series-aware grid, random, Bayesian, and optional genetic searches with resource limits.
  - **Target:** `backend/services/optimization/methods/*`, `backend/services/optimization/execution.py`
  - **Existing foundation:** Existing optimization methods and parallel execution.
  - **Acceptance:** Searches can run with anchored/rolling splits and persist all candidate metrics.
  - **Tests:** Unit tests for search space expansion; integration test for a small search run.
  - **Usage example:**
    ```python
    result = run_hyperparameter_search(strategy_factory, search_space, cv="walk_forward")
    ```

### C6.L4 - Evaluating and Optimizing AI Strategies

- [ ] **Add robustness suite**
  - **Task:** Add shuffled trade order, slippage stress, spread stress, data perturbation, regime split, and seed stability tests.
  - **Target:** `backend/services/optimization/robustness.py`
  - **Existing foundation:** Monte Carlo, walk-forward, failure tests, risk governance.
  - **Acceptance:** Robustness results become promotion gates in strategy governance.
  - **Tests:** Unit tests for each stress transform; integration test for robustness workflow stage.
  - **Usage example:**
    ```python
    robustness = run_robustness_suite(backtest_result, tests=["slippage", "regime_split"])
    ```

- [ ] **Add feature importance and ablation**
  - **Task:** Report feature importance, feature stability, and feature ablation impact.
  - **Target:** `backend/services/optimization/feature_selection.py`, `backend/services/modeling/evaluation.py`
  - **Existing foundation:** Feature pipeline and research reports.
  - **Acceptance:** Strategy cards show which features matter and whether the strategy survives feature removal.
  - **Tests:** Unit tests for ablation summary payloads.
  - **Usage example:**
    ```python
    ablation = run_feature_ablation(model, dataset, metric="validation_auc")
    ```

### C6.L5 - Deployment and Real-World Considerations

- [ ] **Add model registry**
  - **Task:** Store model id, strategy id, data range, feature version, hyperparameters, artifacts, metrics, status, and promotion linkage.
  - **Target:** `backend/services/modeling/model_registry.py`
  - **Existing foundation:** Schema registry, strategy governance persistence, evidence manifests.
  - **Acceptance:** Every trained model used in a workflow has a registry entry.
  - **Tests:** Unit tests for create/read/update lifecycle; integration test linking model to strategy evidence.
  - **Usage example:**
    ```python
    model_id = registry.register(model_artifact, metadata=model_metadata)
    ```

- [ ] **Add drift monitoring**
  - **Task:** Monitor feature drift, prediction drift, live-vs-backtest divergence, missing features, and confidence collapse.
  - **Target:** `backend/services/modeling/drift.py` or `backend/services/optimization/drift_monitor.py`
  - **Existing foundation:** Monitoring service, shadow mode, circuit breaker, observation events.
  - **Acceptance:** Drift findings generate monitoring events and can suspend or block promotion.
  - **Tests:** Unit tests for drift calculations; integration test for shadow drift report.
  - **Usage example:**
    ```python
    drift = monitor_model_drift(reference_features, live_features, predictions)
    ```

- [ ] **Wire strategy promotion gates**
  - **Task:** Make model/strategy promotion require evidence, risk metrics, robustness, drift baseline, operating envelope, and approvals.
  - **Target:** `backend/services/strategy_gov/`, `backend/services/approval/`, `backend/services/evidence/`
  - **Existing foundation:** Strategy governance lifecycle, approval packet builder, evidence service.
  - **Acceptance:** Strategy candidates cannot move to shadow/paper/live without complete evidence.
  - **Tests:** Unit tests for promotion evidence validation; integration test for approve/reject lifecycle.
  - **Usage example:**
    ```python
    decision = strategy_governance.evaluate_promotion(strategy_id, evidence_bundle)
    ```

### C6.L6 - Project: Building and Optimizing a Classification Model for Trading

- [ ] **Implement classification optimization workflow**
  - **Task:** Build preprocessing -> feature selection -> tuning -> calibration -> evaluation -> robustness -> report -> verdict.
  - **Target:** `backend/orchestration/workflow/definitions/classification_optimization.yaml`
  - **Existing foundation:** Modeling service, optimization service, analytics, evidence, reporting.
  - **Acceptance:** Workflow produces a calibrated classifier, metrics, overfit diagnostics, robustness report, and strategy card.
  - **Tests:** Integration test using a fixture dataset and bounded search space.
  - **Usage example:**
    ```powershell
    pytest tests/integration/backend/test_classification_optimization_workflow.py -q
    ```

---

## 7. Course 7 - Momentum-Based Trading

### C7.L1 - What is Momentum-Based Trading

- [ ] **Add momentum statistics toolkit**
  - **Task:** Add normality diagnostics, Shapiro-Wilk wrapper, t-test helper, distribution summaries, and return significance tests.
  - **Target:** `backend/services/strategy/momentum/stats.py`
  - **Existing foundation:** `backend/services/analytics/statistical_tests.py`, distributions.
  - **Acceptance:** Momentum research can test whether observed returns/trends are statistically meaningful.
  - **Tests:** Unit tests comparing output to scipy/sklearn expected values where applicable.
  - **Usage example:**
    ```python
    stats = test_momentum_significance(forward_returns)
    ```

- [ ] **Document momentum strategy taxonomy**
  - **Task:** Define how momentum fits with baselines, supervised models, RL, regime filters, and risk governance.
  - **Target:** `docs/haruquant/HaruQuant_Momentum_Research_Framework.md`
  - **Existing foundation:** Strategy docs, edge lab docs, fundamentals docs.
  - **Acceptance:** The document explains time-series momentum, cross-sectional momentum, filters, risks, and promotion criteria.
  - **Tests:** Manual docs review.
  - **Usage example:**
    ```text
    Momentum family -> baseline, ranked portfolio, classifier-filtered, regime-filtered.
    ```

### C7.L2 - Identifying and Extracting Momentum Features

- [ ] **Add momentum feature set**
  - **Task:** Implement time-series momentum, cross-sectional momentum, breakout distance, trend persistence, relative strength, and volatility-adjusted momentum.
  - **Target:** `backend/services/strategy/momentum/features.py`
  - **Existing foundation:** Indicators, research trend persistence, feature pipeline.
  - **Acceptance:** Momentum features are registered with lookback, lag, and leakage metadata.
  - **Tests:** Unit tests for feature calculations and timestamp alignment.
  - **Usage example:**
    ```python
    momentum_features = build_momentum_features(bars, lookbacks=[20, 60, 120])
    ```

- [ ] **Add GBM helpers**
  - **Task:** Implement geometric Brownian motion calibration, forecast paths, confidence intervals, and scenario assumptions.
  - **Target:** `backend/services/strategy/momentum/gbm.py`
  - **Existing foundation:** Volatility analytics and distributions.
  - **Acceptance:** GBM helpers are optional research tools and their assumptions are recorded in reports.
  - **Tests:** Unit tests for calibration shape and deterministic seeded path generation.
  - **Usage example:**
    ```python
    paths = simulate_gbm_paths(price, mu, sigma, steps=60, paths=1000, seed=42)
    ```

### C7.L3 - Constructing a Momentum Trading Model

- [ ] **Add momentum ranking model**
  - **Task:** Implement ranking, selection, holding-period rules, rebalance schedules, confidence-filtered entries, and allocation outputs.
  - **Target:** `backend/services/strategy/momentum/model.py`
  - **Existing foundation:** Strategy adapter, portfolio agent, risk engine.
  - **Acceptance:** Momentum model can produce `TradeHypothesis`, `TradeProposal`, or portfolio allocation candidates.
  - **Tests:** Unit tests for ranking and rebalance behavior; integration test into backtest adapter.
  - **Usage example:**
    ```python
    allocations = momentum_model.rank_and_allocate(feature_frame, top_n=5)
    ```

- [ ] **Add scenario simulation**
  - **Task:** Run Monte Carlo/scenario stress tests for momentum candidates.
  - **Target:** `backend/services/strategy/momentum/scenario_sim.py`
  - **Existing foundation:** Optimization Monte Carlo and simulation services.
  - **Acceptance:** Scenario outputs are included in momentum strategy cards.
  - **Tests:** Unit tests for deterministic seeded scenarios; integration test for scenario report.
  - **Usage example:**
    ```python
    scenarios = simulate_momentum_scenarios(strategy, bars, seed=42)
    ```

### C7.L4 - Backtesting and Optimization Techniques

- [ ] **Add momentum backtest wrapper**
  - **Task:** Run momentum model through shared simulation/backtest with Sharpe, max drawdown, turnover, hit ratio, and regime sensitivity.
  - **Target:** `backend/services/strategy/momentum/backtest.py`
  - **Existing foundation:** Simulation service, analytics, optimization walk-forward.
  - **Acceptance:** Momentum backtests use the same cost model and report format as other strategies.
  - **Tests:** Integration test for momentum backtest with fixture data.
  - **Usage example:**
    ```python
    result = backtest_momentum_strategy(momentum_model, bars, costs=cost_config)
    ```

- [ ] **Add momentum risk overlays**
  - **Task:** Add VaR, expected shortfall, turnover risk, concentration, and regime risk overlays.
  - **Target:** `backend/services/strategy/momentum/risk.py`
  - **Existing foundation:** Risk engine, analytics risks, portfolio agent.
  - **Acceptance:** Momentum promotion evidence includes VaR/ES and concentration/regime sensitivity.
  - **Tests:** Unit tests for overlay calculations; integration test with strategy card output.
  - **Usage example:**
    ```python
    risk_overlay = evaluate_momentum_risk(backtest_result, portfolio_state)
    ```

- [ ] **Add momentum optimization**
  - **Task:** Optimize lookbacks, rebalance frequency, ranking thresholds, volatility filters, and confidence filters.
  - **Target:** `backend/services/optimization/`, `backend/services/strategy/momentum/model.py`
  - **Existing foundation:** Optimization search methods, walk-forward, robustness suite.
  - **Acceptance:** Momentum optimization uses time-series-aware validation and robustness gates.
  - **Tests:** Integration test with small bounded search space.
  - **Usage example:**
    ```python
    result = optimize_momentum_strategy(search_space, cv="walk_forward")
    ```

### C7.L5 - Project: Build a Momentum-Based Algorithmic Trading Program

- [ ] **Implement momentum project workflow**
  - **Task:** Build features -> ranking model -> scenarios -> backtest -> optimization -> risk overlays -> report -> verdict.
  - **Target:** `backend/orchestration/workflow/definitions/momentum_trading.yaml`
  - **Existing foundation:** Momentum service, optimization, analytics, evidence, reporting, strategy governance.
  - **Acceptance:** Workflow produces a momentum strategy card with equity and FX-compatible assumptions where possible.
  - **Tests:** Integration test with deterministic fixture data; acceptance test for strategy card/evidence.
  - **Usage example:**
    ```powershell
    pytest tests/integration/backend/test_momentum_trading_workflow.py -q
    ```

---

## 8. Course 8 - Congratulations and Final Closeout

### C8.L1 - Final Readiness Review

- [ ] **Add AI trading report builder**
  - **Task:** Build a shared report builder for datasets, models, backtests, optimization, RL, and momentum workflows.
  - **Target:** `backend/services/reporting/ai_trading_report_builder.py`
  - **Existing foundation:** Research reporting, analytics, evidence manifests.
  - **Acceptance:** Reports include data summary, feature summary, model summary, predictive metrics, strategy metrics, risk metrics, robustness, caveats, and verdict.
  - **Tests:** Unit tests for report payload construction; integration test from each project workflow.
  - **Usage example:**
    ```python
    report = build_ai_trading_report(workflow_log, evaluation_report, evidence_manifest)
    ```

- [ ] **Add strategy cards**
  - **Task:** Create a normalized strategy card shape for baseline, regression, classification, RL, and momentum strategies.
  - **Target:** `backend/services/reporting/strategy_card.py`
  - **Existing foundation:** `EvaluationReport`, approval packets, evidence service, strategy governance.
  - **Acceptance:** Strategy cards are suitable for promotion review and operator UI display.
  - **Tests:** Unit tests for required fields; integration test attaching card to promotion evidence.
  - **Usage example:**
    ```python
    card = build_strategy_card(strategy_id, evaluation, robustness, risk, evidence)
    ```

- [ ] **Wire shadow-mode validation**
  - **Task:** Ensure promotion-bound strategy candidates run in shadow mode before paper/live eligibility.
  - **Target:** `backend/services/shadow/`, `backend/services/strategy_gov/`
  - **Existing foundation:** Shadow feeds, execution, reporting, strategy lifecycle.
  - **Acceptance:** Strategy lifecycle cannot advance to paper/live-eligible without a shadow report.
  - **Tests:** Integration test for lifecycle gate blocking missing shadow evidence.
  - **Usage example:**
    ```python
    shadow_report = run_shadow_validation(strategy_id, market_feed="paper-replay")
    ```

- [ ] **Expose strategy workflow artifacts in operator/edge UI**
  - **Task:** Add or reuse UI views to show workflow state, strategy cards, evidence, approvals, replay, and incidents.
  - **Target:** `ui/src/app/(dashboard)/operator/*`, `ui/src/app/(dashboard)/edge-lab/*`, `ui/src/app/(dashboard)/performance/*`
  - **Existing foundation:** Operator shell, workflow view, evidence view, approval view, replay view, edge lab pages.
  - **Acceptance:** Operators can inspect strategy readiness without reading backend logs.
  - **Tests:** Component tests where existing UI test patterns exist; acceptance tests for edge/operator flows.
  - **Usage example:**
    ```text
    Operator -> Strategies -> Strategy card -> Evidence -> Replay bundle -> Approval state
    ```

- [ ] **Complete final coverage audit**
  - **Task:** Mark every lesson and project complete only after code, tests, docs, evidence, and governance gates are in place.
  - **Target:** `docs/haruquant/AI_Trading_Strategies_Final_Coverage_Checklist.md`
  - **Existing foundation:** Traceability register, tests, evidence manifests.
  - **Acceptance:** Every enumerated lesson tag, any later-identified missing/renamed tag, and all 5 project workflows have passing references.
  - **Tests:** Run targeted strategy workflow tests plus existing relevant risk/edge/operator acceptance tests.
  - **Usage example:**
    ```powershell
    pytest tests/unit/backend/services tests/integration/backend tests/acceptance/apps/edge -q
    ```

---

## 9. Five Project Workflow Checklist

- [ ] **Project 1: Data Transformation for Trading Models**
  - **Workflow:** `backend/orchestration/workflow/definitions/data_transformation.yaml`
  - **Covers:** `C3.L1`, `C3.L2`, `C3.L3`, `C3.L4`, `C3.L5`
  - **Outputs:** Clean dataset, EDA report, feature manifest, leakage report, evidence manifest.
  - **Tests:** `tests/integration/backend/test_data_transformation_workflow.py`
  - **Usage example:** Run data transformation on fixture EURUSD H1 bars and verify deterministic output hash.

- [ ] **Project 2: Evaluating and Backtesting a Dynamic Investment Strategy**
  - **Workflow:** `backend/orchestration/workflow/definitions/dynamic_strategy.yaml`
  - **Covers:** `C4.L1`, `C4.L2`, `C4.L3`, `C4.L4`, `C4.L5`
  - **Outputs:** Backtest result, walk-forward report, cost report, risk report, strategy card, evidence manifest.
  - **Tests:** `tests/integration/backend/test_dynamic_strategy_workflow.py`
  - **Usage example:** Run a multi-symbol dynamic allocation strategy through walk-forward validation.

- [ ] **Project 3: Building a Reinforcement Learning Trading Model**
  - **Workflow:** `backend/orchestration/workflow/definitions/rl_trading.yaml`
  - **Covers:** `C5.L1`, `C5.L2`, `C5.L3`, `C5.L4`, `C5.L5`
  - **Outputs:** RL checkpoint, training curves, OOS evaluation, action diagnostics, strategy card.
  - **Tests:** `tests/integration/backend/test_rl_trading_workflow.py`
  - **Usage example:** Train a Q-learning agent on a small fixture dataset and evaluate OOS with fixed seeds.

- [ ] **Project 4: Building and Optimizing a Classification Model for Trading**
  - **Workflow:** `backend/orchestration/workflow/definitions/classification_optimization.yaml`
  - **Covers:** `C2.L4`, `C6.L1`, `C6.L2`, `C6.L3`, `C6.L4`, `C6.L5`, `C6.L6`
  - **Outputs:** Calibrated classifier, tuning result, overfit diagnostics, robustness report, drift baseline, strategy card.
  - **Tests:** `tests/integration/backend/test_classification_optimization_workflow.py`
  - **Usage example:** Optimize a direction classifier with walk-forward splits and threshold calibration.

- [ ] **Project 5: Build a Momentum-Based Algorithmic Trading Program**
  - **Workflow:** `backend/orchestration/workflow/definitions/momentum_trading.yaml`
  - **Covers:** `C7.L1`, `C7.L2`, `C7.L3`, `C7.L4`, `C7.L5`
  - **Outputs:** Momentum feature set, ranking model, scenario simulation, backtest report, risk overlays, strategy card.
  - **Tests:** `tests/integration/backend/test_momentum_trading_workflow.py`
  - **Usage example:** Build a ranked momentum portfolio and evaluate Sharpe, drawdown, turnover, VaR, and expected shortfall.

---

## 10. Global Acceptance Gates

Every checklist item is complete only when:

- [ ] **Implementation exists**
  - Code is in the relevant `backend/services/*`, `backend/agents/*`, `backend/contracts/*`, `backend/orchestration/workflow/definitions/*`, or UI namespace.
- [ ] **Workflow or API entrypoint exists**
  - The capability can run through a declarative workflow or explicit service API.
- [ ] **Contracts are respected**
  - Inputs and outputs use existing canonical contracts or a documented new contract.
- [ ] **Tests exist**
  - Formula and transform logic has unit tests.
  - Multi-stage behavior has integration tests.
  - Operator/edge/risk behavior has acceptance tests where user-visible.
- [ ] **Evidence exists**
  - Runs emit config hash, code hash, data hash, feature manifest, metrics, report, and replay references.
- [ ] **Risk and governance are wired**
  - Promotion-bound strategies pass risk, approval, strategy governance, operating envelope, and shadow-mode requirements.
- [ ] **Reports exist**
  - Human-readable reports and strategy cards are produced.
- [ ] **Traceability is updated**
  - Lesson status, tests, artifacts, and owner modules are recorded in the traceability register.

---

## 11. Recommended Implementation Order

- [ ] **Slice 1: Traceability and workflow skeletons**
  - Create traceability register, final checklist, and five descriptive workflow skeletons.
- [ ] **Slice 2: Data transformation path**
  - Implement C3 data acquisition/preprocessing/features/EDA and Project 1.
- [ ] **Slice 3: Baselines and shared strategy cards**
  - Implement RSI, EMA cross, naive momentum, shared report builder, and strategy card.
- [ ] **Slice 4: Analytics and dynamic strategy**
  - Harden C4 metrics, costs, backtest adapter, walk-forward, and Project 2.
- [ ] **Slice 5: Supervised classification/regression and optimization**
  - Implement modeling services, regularization, search, robustness, drift, model registry, and Project 4.
- [ ] **Slice 6: RL subsystem**
  - Implement RL base/state/action/env/rewards/Q-learning/evaluator and Project 3.
- [ ] **Slice 7: Momentum subsystem**
  - Implement momentum stats/features/GBM/model/scenario/risk/backtest/optimization and Project 5.
- [ ] **Slice 8: Governance, shadow, UI, and final audit**
  - Wire promotion gates, shadow reports, operator/edge UI references, and final coverage signoff.

---

## 12. Final Completion Definition

The AI trading strategies extension is complete when:

- [ ] Every enumerated lesson tag, plus any later-identified missing/renamed tag, is marked covered in the traceability register.
- [ ] All five project workflows exist and run from a clean checkout with fixture data.
- [ ] Baseline, supervised regression, supervised classification, RL, and momentum strategies produce comparable strategy cards.
- [ ] Analytics, backtesting, optimization, and risk outputs are shared with existing HaruQuant services instead of duplicated.
- [ ] Every promotion-bound strategy has evidence, risk assessment, operating envelope, shadow-mode report, approval state, and governance lifecycle status.
- [ ] Operator UI can show workflow progress, evidence, approvals, incidents, and replay references.
- [ ] Unit, integration, acceptance, eval, failure, and performance tests cover the implemented surfaces.
- [ ] Final coverage checklist is complete.

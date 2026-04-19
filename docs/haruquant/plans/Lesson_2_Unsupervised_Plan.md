# Lesson 2 Unsupervised Learning Implementation Plan

Status: canonical lesson workstream plan
Scope: lesson 2 implementation tasks, sequencing, and expected outputs
Use this when: you need the detailed plan for unsupervised learning integration
Companion docs: `ND881_Implementation_Plan.md`, `../traceability/AI_Trading_Traceability.md`
Owner: quant research platform
Review cadence: during active lesson implementation

**Source lesson:** `docs/ai-trading-strategies/02-unsupervised-learning.md`
**Baseline expansion point:** `backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py`
**Prior lesson foundation:** `docs/ai-trading-strategies/01-introduction-to-ai-workflows-in-trading.md`

## Objective

Extend the Lesson 1 AI trading workflow from baseline signal generation and backtesting into a Lesson 2 research layer that discovers market structure before strategy evaluation. The implementation should make unsupervised learning a first-class workflow stage, not a detached notebook-style example.

The Lesson 2 path should produce:

- Investment data summary statistics.
- PCA component scores and loadings.
- Interpretable PCA risk-factor metadata.
- K-Means cluster/regime labels.
- Cluster-level forward-return outperformance.
- Optional strategy signal adaptation based on cluster quality.
- Workflow and example output that can be persisted as evidence later.

## Current State

Already available:

- `backend/services/modeling/unsupervised.py`
  - `run_pca`
  - `cluster_feature_space`
  - `attach_cluster_labels`
- `backend/services/modeling/unsupervised_insights.py`
  - `summarize_investment_data`
  - `identify_pca_risk_factors`
  - `analyze_cluster_outperformance`
  - `adapt_signals_by_cluster`
  - `build_unsupervised_insight_report`
- Unit tests:
  - `tests/unit/backend/services/test_unsupervised_modeling.py`
  - `tests/unit/backend/services/test_unsupervised_insights.py`
- Lesson 1 executable tutorial:
  - `backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py`
- Lesson 1 registry workflow:
  - `backend/orchestration/workflow/definitions/data_transformation.yaml`
  - `backend/orchestration/workflow/steps_data_transformation.py`

Gap:

The existing workflow example executes Lesson 1 data, feature, signal, backtest, evaluation, and refinement logic. It does not yet expose Lesson 2 as a registry step or example section that runs PCA, K-Means, risk-factor interpretation, cluster scoring, and cluster-adapted signal comparison.

## Design Direction

Use the existing HaruQuant services as the implementation boundary:

- Keep modeling math in `backend/services/modeling/`.
- Keep workflow step orchestration in `backend/orchestration/workflow/`.
- Keep tutorial/demo behavior in `backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py`.
- Keep tests under the existing unit and integration test layout.
- Avoid creating a separate course-only package.

Lesson 2 should be an additive research stage between `generate_signals` and `backtest_strategy`:

```text
collect_market_data
clean_and_prepare_data
create_features
define_strategy_or_model
generate_signals
run_unsupervised_research
adapt_signals_by_unsupervised_regime
backtest_strategy
evaluate_performance
refine_and_repeat
```

The first integration can combine `run_unsupervised_research` and signal adaptation into one step if that keeps the initial change small. The workflow YAML should still name the stage clearly so it can be split later.

## Implementation Phases

### Phase 1 - Feature Frame for Lesson 2

Create a deterministic feature frame from the existing Lesson 1 output.

Target:

- `backend/orchestration/workflow/steps_data_transformation.py`
- `backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py`

Implementation:

- Add derived columns needed by unsupervised learning:
  - `return_1`
  - `rolling_volatility`
  - `momentum`
  - `range_pct`
  - optionally EMA spread features already produced by Lesson 1.
- Use only timestamp-aligned historical features.
- Drop rows that cannot support PCA/K-Means after rolling calculations.
- Store the selected `feature_columns` in workflow context and example diagnostics.

Acceptance:

- Feature columns are numeric.
- No feature uses forward returns.
- The feature frame keeps the same datetime index as the signal frame after alignment.

### Phase 2 - Registry Workflow Step

Add a workflow step that builds the unsupervised insight report.

Target:

- `backend/orchestration/workflow/definitions/data_transformation.yaml`
- `backend/orchestration/workflow/steps_data_transformation.py`

Implementation:

- Add YAML step `run_unsupervised_research` after `generate_signals`.
- Register `step_run_unsupervised_research` in `STEP_IMPLEMENTATIONS`.
- Call `build_unsupervised_insight_report` with:
  - cleaned/featured bars as `data`
  - selected numeric feature columns
  - `price_column="close"`
  - `n_components=2`
  - `n_clusters=3`
  - fixed `random_state=42`
  - `signal_frame=signaled`
  - `signal_column="entry_signal"`
- Store in context:
  - `unsupervised_report`
  - `labeled_feature_frame`
  - `cluster_labels`
  - `adapted_signaled` when adaptation is enabled.
- Return compact metadata only, not raw DataFrames.

Acceptance:

- Workflow result includes PCA metadata, K-Means metadata, risk factors, cluster outperformance, and signal adaptation metadata.
- The step is deterministic for fixed data and `random_state`.
- If there are too few rows for PCA/K-Means, the step returns a clear skipped/warn status rather than crashing the whole example.

### Phase 3 - Cluster-Adapted Backtest Option

Allow the Lesson 1 backtest path to compare original shifted signals versus cluster-adapted shifted signals.

Target:

- `backend/orchestration/workflow/steps_data_transformation.py`
- `backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py`

Implementation:

- Add an `use_unsupervised_signal_filter: bool = False` workflow parameter.
- If enabled and `unsupervised_report.signal_adaptation` exists:
  - use adapted `entry_signal` before shift.
  - preserve original signal counts in metadata.
- Keep the default path unchanged to avoid changing Lesson 1 behavior.

Acceptance:

- Default workflow output remains backward-compatible.
- Adapted mode reports:
  - original signal count
  - adapted signal count
  - allowed clusters
  - blocked clusters
  - backtest metrics after adaptation.

### Phase 4 - Agentic Example Expansion

Extend the executable tutorial with Lesson 2 examples.

Target:

- `backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py`

Implementation:

- Update module docstring/title to cover Lesson 1 and Lesson 2.
- Add examples after existing Lesson 1 examples:
  - `example_13_unsupervised_data_summary`
  - `example_14_pca_risk_factor_analysis`
  - `example_15_kmeans_regime_clustering`
  - `example_16_cluster_outperformance_and_signal_filter`
  - `example_17_registry_driven_unsupervised_workflow`
- Reuse shared helper functions from the file.
- Avoid duplicating PCA/K-Means logic; call `backend.services.modeling.unsupervised_insights`.

Acceptance:

- Each example prints compact, interpretable output.
- The registry-driven example proves the workflow step runs from YAML.
- The examples remain safe in environments with limited market data by using existing sample/fallback behavior where possible.

### Phase 5 - Tests

Add coverage for the workflow integration layer.

Targets:

- Existing unit tests remain:
  - `tests/unit/backend/services/test_unsupervised_modeling.py`
  - `tests/unit/backend/services/test_unsupervised_insights.py`
- Add or extend:
  - `tests/integration/backend/test_data_transformation_workflow.py`

Implementation:

- Test `step_run_unsupervised_research` with a fixture `WorkflowContext`.
- Test registry execution includes `run_unsupervised_research`.
- Test adapted-signal mode reduces or preserves signal count, never increases it.
- Test too-few-row behavior returns skipped/warn metadata.

Acceptance commands:

```powershell
pytest tests/unit/backend/services/test_unsupervised_modeling.py -q
pytest tests/unit/backend/services/test_unsupervised_insights.py -q
pytest tests/integration/backend/test_data_transformation_workflow.py -q
```

### Phase 6 - Traceability and Reporting

Update docs once the workflow step is implemented.

Targets:

- `docs/haruquant/traceability/AI_Trading_Traceability.md`
- `docs/haruquant/plans/ND881_Implementation_Plan.md`

Implementation:

- Keep C2.L2 marked implemented only after workflow integration and example expansion are complete.
- Add evidence artifact names:
  - `unsupervised_data_summary`
  - `pca_metadata`
  - `kmeans_cluster_metadata`
  - `pca_risk_factors`
  - `cluster_outperformance`
  - `cluster_signal_adaptation`
- Record the workflow step and tests.

Acceptance:

- A reader can trace Lesson 2 from source lesson to service module, workflow step, example, tests, and artifact output.

## Proposed Data Contract

Workflow step result:

```python
{
    "status": "COMPLETED",
    "feature_columns": ["return_1", "rolling_volatility", "momentum", "range_pct"],
    "pca": {
        "model": "pca",
        "n_components": 2,
        "explained_variance_ratio": [...],
        "scaled": True,
    },
    "clusters": {
        "model": "kmeans",
        "n_clusters": 3,
        "inertia": 0.0,
        "random_state": 42,
        "scaled": True,
    },
    "risk_factors": [...],
    "cluster_outperformance": [...],
    "signal_adaptation": {
        "allowed_clusters": [...],
        "blocked_clusters": [...],
        "original_signal_count": 0,
        "adapted_signal_count": 0,
    },
}
```

Do not return full DataFrames from workflow results. Store them in `WorkflowContext` for downstream steps, and return only serializable metadata.

## Risk Controls

- Do not cluster raw prices.
- Standardize features before PCA/K-Means.
- Keep forward returns out of the feature matrix.
- Use `shift(1)` before backtesting adapted signals.
- Treat clusters as research filters, not direct buy/sell instructions.
- Make cluster adaptation opt-in until enough validation exists.
- Keep fixed seeds in tests and examples.

## Completion Criteria

Lesson 2 is complete when:

- `data_transformation.yaml` includes a Lesson 2 unsupervised research stage.
- The workflow step produces PCA, K-Means, risk-factor, cluster-performance, and adaptation metadata.
- `04_ai_trading_strategy_workflows.py` demonstrates Lesson 2 examples without duplicating model logic.
- Existing unit tests pass.
- Workflow integration tests cover the new step and adapted-signal option.
- Traceability docs point to the workflow step, examples, tests, and artifacts.

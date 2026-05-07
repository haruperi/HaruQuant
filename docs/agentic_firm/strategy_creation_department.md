# HaruQuant Agentic AI Trading Firm
# Strategy Creation Department

## Goal

Turn approved research ideas, validated hypotheses, and user prompts into formal, testable, reviewable, code-ready HaruQuant strategy packages.

The Strategy Creation Department is responsible for moving a strategy idea from vague concept to structured specification, implementation plan, generated strategy code, reviewer feedback, and a validated handoff package for backtesting and robustness testing.

The department does **not** execute trades, approve risk, deploy live strategies, bypass validation, or override the Risk Governor.

Every agent in this department must follow the HaruQuant Agent Template execution pattern:

```text
Validate Input
-> Gather Evidence / Context
-> Optional LLM Reasoning
-> Deterministic Policy Decision
-> Structured Output
-> Audit Log
-> Evaluation Test
```

Core rule:

```text
LLM output = proposal
Deterministic policy = final decision
```

The Strategy Creation Department must also follow the HaruQuant Strategy Creation Template rule:

```text
on_bar() creates market truth.
get_signal() converts simple market truth into SignalDict.
on_event() converts market truth + portfolio state into TradeAction objects.
risk controls decide whether those actions are allowed.
execution engine performs approved actions.
```

---

## Dependency

Phase 8: Research Department complete.

The Strategy Creation Department consumes outputs from the Research Department, especially:

- approved research reports
- validated strategy hypotheses
- market intelligence reports
- technical analysis reports
- macro/fundamental context reports
- news/sentiment risk warnings
- cross-asset/correlation warnings
- seasonality reports
- evidence references
- research validation status
- rejected idea memory
- strategy idea lineage

---

## 1. Department Scope

### 1.1 Primary Responsibilities

* [ ] Convert natural language strategy requests into structured strategy specifications.
* [ ] Convert approved research hypotheses into structured strategy specifications.
* [ ] Convert strategy specs into implementation-ready strategy design packages.
* [ ] Generate HaruQuant-compatible strategy code.
* [ ] Review generated strategy code against HaruQuant strategy standards.
* [ ] Validate strategy specs before code generation.
* [ ] Validate generated code before backtesting handoff.
* [ ] Support both simple and complex stateful strategies.
* [ ] Enforce the universal strategy lifecycle.
* [ ] Enforce `on_bar()` as the universal feature/signal-preparation layer.
* [ ] Enforce `get_signal()` for simple signal parsing.
* [ ] Enforce `on_event()` for complex stateful trade management.
* [ ] Ensure complex strategies consume `on_bar()` activators wherever possible.
* [ ] Define symbol, timeframe, market regime, and strategy family.
* [ ] Define entry logic.
* [ ] Define exit logic.
* [ ] Define position management logic.
* [ ] Define risk-control assumptions.
* [ ] Define position sizing assumptions.
* [ ] Define execution assumptions.
* [ ] Define spread, slippage, commission, and swap assumptions.
* [ ] Define data requirements.
* [ ] Define indicator requirements.
* [ ] Define state requirements for complex strategies.
* [ ] Define invalidation rules.
* [ ] Define test plans.
* [ ] Define robustness requirements.
* [ ] Save and version strategy specs.
* [ ] Save and version generated strategy code artifacts.
* [ ] Link every spec and generated strategy to research evidence.
* [ ] Produce handoff packages for Validation & Backtesting Department.

### 1.2 Non-Goals

* [ ] Do not execute trades.
* [ ] Do not approve live trading.
* [ ] Do not approve risk.
* [ ] Do not override the Risk Governor.
* [ ] Do not bypass backtesting.
* [ ] Do not bypass robustness testing.
* [ ] Do not mark a strategy as production-ready.
* [ ] Do not silently invent missing market data.
* [ ] Do not silently invent unavailable indicators or services.
* [ ] Do not produce vague or untestable strategy rules.
* [ ] Do not create future-looking rules.
* [ ] Do not allow lookahead bias.
* [ ] Do not directly modify live trading configuration.
* [ ] Do not directly connect specialist agents to the chat UI.
* [ ] Do not generate broker execution code inside strategy files.

---

## 2. Department Architecture

### 2.1 Core Agents

The department must include these three core agents:

* [ ] Strategy Creator Agent.
* [ ] Strategy Codegen Agent.
* [ ] Strategy Reviewer Agent.

These are the core production workflow agents:

```text
Research/User Request
-> Strategy Creator Agent
-> Strategy Spec Validator / Rule Normalizer / Template Selector
-> Strategy Codegen Agent
-> Strategy Reviewer Agent
-> Strategy Storage / Handoff
-> Validation & Backtesting Department
```

### 2.2 Supporting Specialist Agents

The department may include supporting agents/services to keep the core agents focused and deterministic:

* [ ] Strategy Creation Orchestrator Agent.
* [ ] Strategy Spec Validator Agent.
* [ ] Strategy Rule Normalizer Agent.
* [ ] Strategy Template Selector Agent.
* [ ] Strategy Risk Assumption Agent.
* [ ] Strategy Cost & Execution Assumption Agent.
* [ ] Strategy Test Plan Agent.
* [ ] Strategy Spec Storage Agent.
* [ ] Strategy Code Storage Agent.
* [ ] Strategy Handoff Agent.

### 2.3 Required Folder Structure

```text
agents/
  strategy_development/
    strategy_creation_orchestrator_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    strategy_creator_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    strategy_codegen_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    strategy_reviewer_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    strategy_spec_validator_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_rule_normalizer_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_template_selector_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_risk_assumption_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_cost_execution_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_test_plan_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_spec_storage_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    strategy_handoff_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

    shared/
      contracts.py
      scoring.py
      strategy_template_rules.py
      code_quality_rules.py
      handoff.py
      constants.py
```

### 2.4 Generated Strategy Folder Structure

Generated production strategies should use this structure:

```text
haruquant/
  strategies/
    <strategy_name>/
      __init__.py
      strategy.py
      config.py
      README.md
      tests/
        test_params.py
        test_on_bar.py
        test_get_signal.py
        test_no_lookahead.py
        test_on_event.py
        test_state_reset.py
        test_action_metadata.py
        test_risk_limits.py
        test_group_ids.py
```

Minimum generated strategy tests:

```text
test_params.py
test_on_bar.py
test_no_lookahead.py
```

Additional tests for complex strategies:

```text
test_on_event.py
test_state_reset.py
test_action_metadata.py
test_risk_limits.py
test_group_ids.py
```

---

## 3. Shared Strategy Creation Standard

### 3.1 Universal Strategy Lifecycle

* [ ] Validate strategy parameters.
* [ ] Initialize strategy state.
* [ ] Calculate features in `on_bar()`.
* [ ] Generate signal columns and activator columns in `on_bar()`.
* [ ] Parse simple signals with `get_signal()`.
* [ ] Use `on_event()` only for stateful position/order/basket management.
* [ ] Return `SignalDict` for simple strategies.
* [ ] Return `list[TradeAction]` for stateful strategies.
* [ ] Send proposed actions to risk controls.
* [ ] Let execution engine execute only approved actions.

### 3.2 Strategy Types Supported

* [ ] EMA crossover.
* [ ] RSI mean reversion.
* [ ] Breakout.
* [ ] Pending order strategy.
* [ ] Session breakout strategy.
* [ ] Volatility expansion strategy.
* [ ] Trend-following strategy.
* [ ] Pullback strategy.
* [ ] Reversal strategy.
* [ ] Martingale strategy.
* [ ] Pyramiding strategy.
* [ ] Trade decomposition strategy.
* [ ] Hedge/grid strategy.
* [ ] Basket strategy.
* [ ] Multi-timeframe structure strategy.
* [ ] Hybrid simple/stateful strategy.

### 3.3 Universal Strategy Contract Requirements

* [ ] Strategy must inherit from `BaseStrategy`.
* [ ] Stateful strategy must also use `StatefulStrategyMixin`.
* [ ] Strategy must define `strategy_name`.
* [ ] Strategy must define `strategy_type`: `simple`, `stateful`, or `hybrid`.
* [ ] Strategy must define `signal_schema_version`.
* [ ] Stateful strategy must define `action_schema_version`.
* [ ] Strategy must implement `__init__()`.
* [ ] Strategy must load parameters explicitly.
* [ ] Strategy must validate parameters explicitly.
* [ ] Strategy must implement `on_init()`.
* [ ] Strategy must implement `on_bar()`.
* [ ] Simple strategy must implement or inherit safe `get_signal()`.
* [ ] Stateful strategy must implement `on_event()`.
* [ ] Strategy must not execute trades directly.
* [ ] Strategy must not call broker APIs directly.
* [ ] Strategy must not approve risk.
* [ ] Strategy must not mutate portfolio state directly.

### 3.4 Required `on_bar()` Signal Columns

Every generated strategy must ensure these columns exist:

* [ ] `entry_signal`.
* [ ] `exit_signal`.
* [ ] `pending_signal`.
* [ ] `cancel_pending_signal`.
* [ ] `pending_signal_2`.
* [ ] `cancel_pending_signal_2`.
* [ ] `price`.
* [ ] `price_2`.
* [ ] `stop_loss`.
* [ ] `take_profit`.
* [ ] `signal_reason`.
* [ ] `setup_id`.
* [ ] `group_id`.

### 3.5 Standard Complex Strategy Activator Columns

Complex strategies should use activator columns in `on_bar()`:

* [ ] `buy_setup_active`.
* [ ] `sell_setup_active`.
* [ ] `buy_add_active`.
* [ ] `sell_add_active`.
* [ ] `buy_exit_active`.
* [ ] `sell_exit_active`.
* [ ] `buy_pyramid_active`.
* [ ] `sell_pyramid_active`.
* [ ] `buy_martingale_active`.
* [ ] `sell_martingale_active`.
* [ ] `buy_decompose_active`.
* [ ] `sell_decompose_active`.
* [ ] `buy_trail_active`.
* [ ] `sell_trail_active`.

### 3.6 Lookahead Bias Rules

* [ ] If execution occurs at bar N open, signals must be based on bar N-1 or earlier.
* [ ] Shift indicator values before they are used for current-bar execution.
* [ ] Do not use current bar close for a signal executed at current bar open.
* [ ] Higher-timeframe features must update only after higher-timeframe candle close.
* [ ] Multi-timeframe joins must avoid forward filling unavailable future values.
* [ ] README must document whether the strategy executes at open, close, or event boundary.
* [ ] Tests must verify no lookahead bias.

### 3.7 TradeAction Metadata Rules

Every generated `TradeAction` must include:

* [ ] `action_type`.
* [ ] `symbol`.
* [ ] `side`.
* [ ] `volume`.
* [ ] `price`.
* [ ] `stop_loss`.
* [ ] `take_profit`.
* [ ] `ticket` where applicable.
* [ ] `setup_id`.
* [ ] `group_id`.
* [ ] `metadata`.
* [ ] `reason`.

Metadata must include:

* [ ] strategy name.
* [ ] strategy ID.
* [ ] setup type.
* [ ] step number for martingale/grid/pyramiding where applicable.
* [ ] source: `on_event` or `get_signal`.
* [ ] signal schema version.
* [ ] action schema version where applicable.
* [ ] parent/child relation for decomposition strategies.

---

## 4. Strategy Creation Orchestrator Agent

### 4.1 Purpose

Coordinate the department workflow from request intake to final handoff package.

### 4.2 Checklist

* [ ] Create `agents/strategy_development/strategy_creation_orchestrator_agent`.
* [ ] Validate incoming request.
* [ ] Determine whether request came from user, CEO Agent, Planner Agent, or Research Department.
* [ ] Determine whether request is a new strategy, revision, code generation request, or review request.
* [ ] Determine required agents.
* [ ] Determine missing inputs.
* [ ] Gather research evidence.
* [ ] Gather approved hypothesis.
* [ ] Gather existing strategy memory.
* [ ] Gather rejected strategy memory.
* [ ] Run Strategy Creator Agent.
* [ ] Run Strategy Spec Validator Agent.
* [ ] Run Strategy Rule Normalizer Agent.
* [ ] Run Strategy Template Selector Agent.
* [ ] Run Strategy Risk Assumption Agent.
* [ ] Run Strategy Cost & Execution Assumption Agent.
* [ ] Run Strategy Test Plan Agent.
* [ ] Run Strategy Codegen Agent when the spec is code-ready.
* [ ] Run Strategy Reviewer Agent after code generation.
* [ ] Run Strategy Spec Storage Agent.
* [ ] Run Strategy Handoff Agent.
* [ ] Resolve conflicts between agents.
* [ ] Block handoff if required contracts are missing.
* [ ] Produce final strategy creation package.
* [ ] Save audit metadata.

### 4.3 Deterministic Policy Rules

* [ ] If no symbol is supplied and cannot be inferred from approved research, return `NEEDS_MORE_CONTEXT`.
* [ ] If no timeframe is supplied and cannot be inferred from approved research, return `NEEDS_MORE_CONTEXT`.
* [ ] If strategy rules are untestable, block code generation.
* [ ] If research validation status is rejected, block strategy creation unless explicitly creating a rejected-memory review.
* [ ] If generated code fails review, block backtesting handoff.
* [ ] If risk assumptions are missing, block validation handoff.
* [ ] If cost assumptions are missing, block validation handoff.

---

## 5. Strategy Creator Agent

### 5.1 Purpose

Convert natural language requests, approved research ideas, and validated hypotheses into a formal `StrategySpec`.

The Strategy Creator Agent creates the **strategy design**, not the final production code.

### 5.2 Inputs

* [ ] User prompt.
* [ ] Approved research hypothesis.
* [ ] Research report ID.
* [ ] Evidence references.
* [ ] Symbol.
* [ ] Timeframe.
* [ ] Strategy family.
* [ ] Market regime.
* [ ] Technical context.
* [ ] Macro/news context.
* [ ] User constraints.
* [ ] Existing strategy memory.
* [ ] Rejected strategy memory.

### 5.3 Checklist

* [ ] Create `agents/strategy_development/strategy_creator_agent`.
* [ ] Convert natural language request into `StrategySpec`.
* [ ] Convert approved research hypothesis into `StrategySpec`.
* [ ] Support simple strategies.
* [ ] Support stateful strategies.
* [ ] Support hybrid strategies.
* [ ] Support symbol.
* [ ] Support timeframe.
* [ ] Support execution timeframe.
* [ ] Support signal timeframe.
* [ ] Support filter timeframe.
* [ ] Support higher timeframe.
* [ ] Support lower timeframe.
* [ ] Support strategy family.
* [ ] Support market regime.
* [ ] Support entry logic.
* [ ] Support exit logic.
* [ ] Support position sizing.
* [ ] Support position management.
* [ ] Support risk assumptions.
* [ ] Support data requirements.
* [ ] Support indicator requirements.
* [ ] Support cost assumptions.
* [ ] Support execution assumptions.
* [ ] Support invalidation rules.
* [ ] Support test plan.
* [ ] Support robustness plan.
* [ ] Support state requirements for complex strategies.
* [ ] Support `on_bar()` feature preparation requirements.
* [ ] Support `get_signal()` requirements for simple strategies.
* [ ] Support `on_event()` requirements for stateful strategies.
* [ ] Support standard signal columns.
* [ ] Support standard activator columns.
* [ ] Support `SignalDict` output rules.
* [ ] Support `TradeAction` output rules.
* [ ] Define lookahead-bias handling.
* [ ] Define parameter list with types and defaults.
* [ ] Define parameter validation rules.
* [ ] Define local strategy risk controls.
* [ ] Define generated strategy folder target.
* [ ] Define expected generated files.
* [ ] Define README requirements.
* [ ] Output strategy spec.
* [ ] Output implementation brief.
* [ ] Save creation evidence to audit.

### 5.4 Strategy Creator LLM Responsibilities

* [ ] Interpret user intent.
* [ ] Draft initial strategy logic.
* [ ] Translate informal strategy descriptions into structured rules.
* [ ] Suggest parameter names and defaults.
* [ ] Suggest indicator requirements.
* [ ] Suggest strategy type: simple, stateful, or hybrid.
* [ ] Suggest whether `on_event()` is required.
* [ ] Suggest test plan.
* [ ] Suggest invalidation rules.

### 5.5 Strategy Creator Deterministic Policy Rules

* [ ] Final `StrategySpec` must be schema-valid.
* [ ] Strategy must have symbol.
* [ ] Strategy must have timeframe.
* [ ] Strategy must have strategy type.
* [ ] Strategy must have entry logic.
* [ ] Strategy must have exit logic.
* [ ] Strategy must have data requirements.
* [ ] Strategy must have cost assumptions.
* [ ] Strategy must have execution assumptions.
* [ ] Strategy must have risk assumptions.
* [ ] Strategy must have test plan.
* [ ] Strategy must define whether it is simple, stateful, or hybrid.
* [ ] Stateful or hybrid strategies must define `on_event()` role.
* [ ] Complex strategies must define activator columns generated in `on_bar()`.
* [ ] Strategy must not contain broker execution calls.
* [ ] Strategy must not contain risk-approval logic.
* [ ] Strategy must not contain future-looking logic.
* [ ] Strategy must not be marked code-ready until validation passes.

### 5.6 Output Artifacts

* [ ] `StrategySpec` JSON/YAML.
* [ ] Strategy implementation brief.
* [ ] Parameter catalog.
* [ ] Signal column plan.
* [ ] Event activator plan.
* [ ] Position management plan.
* [ ] Risk-control assumptions.
* [ ] Cost/execution assumptions.
* [ ] Test plan.
* [ ] Handoff readiness status.

---

## 6. Strategy Spec Validator Agent

### 6.1 Purpose

Validate that a `StrategySpec` is complete, testable, non-vague, non-future-looking, and compatible with the HaruQuant strategy template.

### 6.2 Checklist

* [ ] Create `agents/strategy_development/strategy_spec_validator_agent`.
* [ ] Reject missing symbol.
* [ ] Reject missing timeframe.
* [ ] Reject missing strategy type.
* [ ] Reject missing strategy family.
* [ ] Reject untestable strategy.
* [ ] Reject vague entry rules.
* [ ] Reject vague exit rules.
* [ ] Reject vague position management rules.
* [ ] Reject missing cost assumptions.
* [ ] Reject missing data requirements.
* [ ] Reject missing execution assumptions.
* [ ] Reject missing risk assumptions.
* [ ] Reject impossible live conditions.
* [ ] Reject future-looking rules.
* [ ] Reject lookahead-prone logic.
* [ ] Reject ambiguous indicator definitions.
* [ ] Reject missing parameter defaults.
* [ ] Reject missing parameter validation rules.
* [ ] Reject missing invalidation rules.
* [ ] Reject missing test plan.
* [ ] Reject missing robustness plan.
* [ ] Reject stateful strategies without state definition.
* [ ] Reject complex strategies without `on_event()` design.
* [ ] Reject complex strategies that calculate core market setup only in `on_event()`.
* [ ] Reject strategies that bypass `on_bar()` feature/activator preparation.
* [ ] Reject strategies that directly execute trades.
* [ ] Reject strategies that approve risk internally.
* [ ] Reject strategies that modify live portfolio state.
* [ ] Output validation report.
* [ ] Output fix recommendations.

### 6.3 Deterministic Policy Rules

* [ ] `APPROVED_FOR_CODEGEN` only if all required fields pass.
* [ ] `NEEDS_REVISION` if missing fields are fixable.
* [ ] `REJECTED` if rules are untestable, future-looking, or unsafe.
* [ ] `REJECTED` if strategy cannot be expressed through HaruQuant lifecycle.
* [ ] `REJECTED` if strategy requires unavailable data.
* [ ] `REJECTED` if strategy requires direct execution from the strategy file.

---

## 7. Strategy Rule Normalizer Agent

### 7.1 Purpose

Normalize vague or natural-language strategy rules into deterministic, testable rule blocks.

### 7.2 Checklist

* [ ] Create `agents/strategy_development/strategy_rule_normalizer_agent`.
* [ ] Normalize entry rules.
* [ ] Normalize exit rules.
* [ ] Normalize pending order rules.
* [ ] Normalize cancellation rules.
* [ ] Normalize stop-loss rules.
* [ ] Normalize take-profit rules.
* [ ] Normalize trailing-stop rules.
* [ ] Normalize breakeven rules.
* [ ] Normalize pyramiding rules.
* [ ] Normalize martingale rules.
* [ ] Normalize grid rules.
* [ ] Normalize hedge rules.
* [ ] Normalize decomposition rules.
* [ ] Normalize multi-timeframe alignment rules.
* [ ] Normalize session filters.
* [ ] Normalize news filters.
* [ ] Normalize spread filters.
* [ ] Normalize volatility filters.
* [ ] Convert subjective words into numeric thresholds.
* [ ] Convert indicator references into exact period/source definitions.
* [ ] Convert timeframe references into explicit fields.
* [ ] Convert risk words into explicit risk-control fields.
* [ ] Output normalized rule set.

### 7.3 Deterministic Policy Rules

* [ ] If a rule cannot be made deterministic, mark it as unresolved.
* [ ] If unresolved rules affect entry, exit, or risk, block code generation.
* [ ] If normalized rules conflict, return `NEEDS_REVISION`.
* [ ] If normalized rules introduce lookahead risk, return `REJECTED`.

---

## 8. Strategy Template Selector Agent

### 8.1 Purpose

Select the correct implementation pattern for the strategy: simple, stateful, or hybrid.

### 8.2 Checklist

* [ ] Create `agents/strategy_development/strategy_template_selector_agent`.
* [ ] Determine whether strategy is simple.
* [ ] Determine whether strategy is stateful.
* [ ] Determine whether strategy is hybrid.
* [ ] Determine whether `get_signal()` is sufficient.
* [ ] Determine whether `on_event()` is required.
* [ ] Select simple `BaseStrategy` template.
* [ ] Select stateful `StatefulStrategyMixin + BaseStrategy` template.
* [ ] Select hybrid template when both `get_signal()` and `on_event()` are needed.
* [ ] Select martingale template.
* [ ] Select pyramiding template.
* [ ] Select trade decomposition template.
* [ ] Select hedge/grid template.
* [ ] Select multi-timeframe template.
* [ ] Select pending order template.
* [ ] Select breakout template.
* [ ] Define required files for generated strategy.
* [ ] Define required tests for generated strategy.
* [ ] Output template selection report.

### 8.3 Deterministic Policy Rules

* [ ] If strategy has basket, layers, martingale, grid, pyramiding, decomposition, or position lifecycle state, require `on_event()`.
* [ ] If strategy only emits bar-level entry/exit signals, use simple `get_signal()` path.
* [ ] If strategy has simple entries but stateful exits or scaling, classify as hybrid.
* [ ] If multi-timeframe logic is used, require explicit timeframe alignment rules.
* [ ] If strategy type cannot be classified, return `NEEDS_MORE_CONTEXT`.

---

## 9. Strategy Risk Assumption Agent

### 9.1 Purpose

Define strategy-level risk assumptions and local risk-control compatibility, without approving risk.

### 9.2 Checklist

* [ ] Create `agents/strategy_development/strategy_risk_assumption_agent`.
* [ ] Define initial position size assumptions.
* [ ] Define fixed-lot assumptions.
* [ ] Define percent-risk assumptions where applicable.
* [ ] Define max open positions per strategy.
* [ ] Define max layers per setup.
* [ ] Define max martingale step.
* [ ] Define max total lots.
* [ ] Define max symbol exposure.
* [ ] Define max strategy drawdown assumption.
* [ ] Define whether multiple action batches per event are allowed.
* [ ] Define local sanity checks.
* [ ] Define global Risk Governor handoff requirements.
* [ ] Define risk fields needed for backtesting.
* [ ] Define risk fields needed for live simulation.
* [ ] Flag risk-dangerous designs.
* [ ] Flag uncapped martingale/grid designs.
* [ ] Flag strategies with unlimited scaling.
* [ ] Flag strategies without exit logic.
* [ ] Output risk assumption report.

### 9.3 Deterministic Policy Rules

* [ ] Reject uncapped martingale.
* [ ] Reject uncapped grid.
* [ ] Reject unlimited pyramiding.
* [ ] Reject unlimited position decomposition.
* [ ] Reject strategies without max position or max exposure constraints.
* [ ] Reject strategies where local risk assumptions conflict with global Risk Governor constraints.
* [ ] Mark all risk decisions as assumptions only, not approval.

---

## 10. Strategy Cost & Execution Assumption Agent

### 10.1 Purpose

Define realistic cost and execution assumptions for the strategy spec and test plan.

### 10.2 Checklist

* [ ] Create `agents/strategy_development/strategy_cost_execution_agent`.
* [ ] Define spread assumptions.
* [ ] Define slippage assumptions.
* [ ] Define commission assumptions.
* [ ] Define swap assumptions.
* [ ] Define minimum stop distance assumptions.
* [ ] Define pip/tick size assumptions.
* [ ] Define lot step assumptions.
* [ ] Define minimum lot assumptions.
* [ ] Define maximum lot assumptions.
* [ ] Define order type assumptions.
* [ ] Define market order assumptions.
* [ ] Define pending order assumptions.
* [ ] Define stop-loss assumptions.
* [ ] Define take-profit assumptions.
* [ ] Define partial close assumptions.
* [ ] Define modify-order assumptions.
* [ ] Define session restrictions.
* [ ] Define rollover restrictions.
* [ ] Define news blackout restrictions.
* [ ] Flag unrealistic execution requirements.
* [ ] Flag strategies too sensitive to spread.
* [ ] Flag strategies too sensitive to slippage.
* [ ] Output cost/execution assumption report.

### 10.3 Deterministic Policy Rules

* [ ] Block code-ready status if cost assumptions are missing.
* [ ] Block code-ready status if execution assumptions are impossible in MT5/cTrader.
* [ ] Block code-ready status if order types are unsupported.
* [ ] Block code-ready status if partial close/modify logic is required but unsupported by the target engine.

---

## 11. Strategy Test Plan Agent

### 11.1 Purpose

Create the required backtest, unit test, and robustness test plan for each strategy.

### 11.2 Checklist

* [ ] Create `agents/strategy_development/strategy_test_plan_agent`.
* [ ] Define unit tests for parameters.
* [ ] Define unit tests for `on_bar()`.
* [ ] Define unit tests for `get_signal()` where applicable.
* [ ] Define unit tests for `on_event()` where applicable.
* [ ] Define no-lookahead tests.
* [ ] Define state reset tests.
* [ ] Define action metadata tests.
* [ ] Define risk-limit tests.
* [ ] Define group ID tests.
* [ ] Define simple smoke backtest.
* [ ] Define full historical backtest.
* [ ] Define IS/OOS split.
* [ ] Define walk-forward or walk-forward matrix requirements where appropriate.
* [ ] Define spread stress test.
* [ ] Define slippage stress test.
* [ ] Define Monte Carlo tests.
* [ ] Define parameter sensitivity tests.
* [ ] Define cross-market test where relevant.
* [ ] Define cross-timeframe test where relevant.
* [ ] Define minimum acceptance criteria.
* [ ] Define rejection criteria.
* [ ] Output test plan artifact.

### 11.3 Deterministic Policy Rules

* [ ] Every strategy must have `test_params.py`, `test_on_bar.py`, and `test_no_lookahead.py`.
* [ ] Stateful strategies must have `test_on_event.py`, `test_state_reset.py`, `test_action_metadata.py`, and `test_risk_limits.py`.
* [ ] Multi-position strategies must have `test_group_ids.py`.
* [ ] Strategies without a test plan are not code-ready.
* [ ] Generated code without tests is not review-approved.

---

## 12. Strategy Codegen Agent

### 12.1 Purpose

Generate HaruQuant-compatible strategy implementation files from an approved `StrategySpec`.

The Strategy Codegen Agent writes strategy code artifacts, but it does **not** approve them for backtesting. The Strategy Reviewer Agent must review them first.

### 12.2 Inputs

* [ ] Approved `StrategySpec`.
* [ ] Template selection report.
* [ ] Normalized rule set.
* [ ] Risk assumption report.
* [ ] Cost/execution assumption report.
* [ ] Test plan artifact.
* [ ] Existing BaseStrategy conventions.
* [ ] Existing StatefulStrategyMixin conventions.
* [ ] Target folder path.
* [ ] Code generation constraints.

### 12.3 Checklist

* [ ] Create `agents/strategy_development/strategy_codegen_agent`.
* [ ] Generate strategy folder.
* [ ] Generate `__init__.py`.
* [ ] Generate `strategy.py`.
* [ ] Generate `config.py`.
* [ ] Generate `README.md`.
* [ ] Generate `tests/test_params.py`.
* [ ] Generate `tests/test_on_bar.py`.
* [ ] Generate `tests/test_no_lookahead.py`.
* [ ] Generate `tests/test_get_signal.py` for simple strategies.
* [ ] Generate `tests/test_on_event.py` for stateful/hybrid strategies.
* [ ] Generate `tests/test_state_reset.py` for stateful/hybrid strategies.
* [ ] Generate `tests/test_action_metadata.py` for stateful/hybrid strategies.
* [ ] Generate `tests/test_risk_limits.py` for stateful/hybrid strategies.
* [ ] Generate `tests/test_group_ids.py` for multi-position strategies.
* [ ] Implement `BaseStrategy` inheritance.
* [ ] Implement `StatefulStrategyMixin` inheritance when required.
* [ ] Implement `strategy_name`.
* [ ] Implement `strategy_type`.
* [ ] Implement `signal_schema_version`.
* [ ] Implement `action_schema_version` when required.
* [ ] Implement parameter loading.
* [ ] Implement parameter validation.
* [ ] Implement `on_init()`.
* [ ] Implement `on_bar()`.
* [ ] Implement `_calculate_indicators()`.
* [ ] Implement `_shift_features()`.
* [ ] Implement `_ensure_signal_columns()`.
* [ ] Implement `_generate_simple_signals()` where applicable.
* [ ] Implement `_generate_event_activators()` where applicable.
* [ ] Implement `get_signal()` or safely inherit base parser.
* [ ] Implement `on_event()` for stateful/hybrid strategies.
* [ ] Implement `_should_process_event()`.
* [ ] Implement `_process_side()` where applicable.
* [ ] Implement `_initial_entry_actions()` where applicable.
* [ ] Implement `_exit_actions()` where applicable.
* [ ] Implement `_add_position_actions()` where applicable.
* [ ] Implement `_modify_position_actions()` where applicable.
* [ ] Implement `_post_process_actions()` where applicable.
* [ ] Implement `_make_group_id()` where applicable.
* [ ] Ensure standard signal columns are always created.
* [ ] Ensure standard activator columns are created for complex strategies.
* [ ] Ensure indicator shifting prevents lookahead bias.
* [ ] Ensure every `TradeAction` includes reason and metadata.
* [ ] Ensure no broker/execution API calls exist in strategy code.
* [ ] Ensure no risk approval code exists in strategy code.
* [ ] Ensure code is formatted.
* [ ] Ensure generated files are review-ready.
* [ ] Output generated code package.

### 12.4 Strategy Codegen LLM Responsibilities

* [ ] Draft implementation code.
* [ ] Draft config defaults.
* [ ] Draft README.
* [ ] Draft tests.
* [ ] Translate structured rules into code.
* [ ] Explain implementation decisions.

### 12.5 Strategy Codegen Deterministic Policy Rules

* [ ] Generate code only from an approved `StrategySpec`.
* [ ] Generate code only after template selection is complete.
* [ ] Generate code only after risk assumptions exist.
* [ ] Generate code only after cost/execution assumptions exist.
* [ ] Generate code only after test plan exists.
* [ ] Block code generation if strategy is untestable.
* [ ] Block code generation if strategy type is unresolved.
* [ ] Block code generation if target engine compatibility is unresolved.
* [ ] Block code generation if required BaseStrategy interfaces are unknown.
* [ ] Generated code status must be `generated_pending_review`.
* [ ] Generated code must not be marked approved by Codegen Agent.

### 12.6 Output Artifacts

* [ ] Strategy code package.
* [ ] Generated file manifest.
* [ ] Codegen assumptions.
* [ ] Codegen warnings.
* [ ] Generated tests.
* [ ] README.
* [ ] Review handoff package.

---

## 13. Strategy Reviewer Agent

### 13.1 Purpose

Review generated strategy specs and code against HaruQuant strategy standards before backtesting handoff.

The Strategy Reviewer Agent does not approve live deployment. It only approves whether the strategy package is ready for validation/backtesting.

### 13.2 Inputs

* [ ] `StrategySpec`.
* [ ] Generated code package.
* [ ] Generated tests.
* [ ] README.
* [ ] Template selection report.
* [ ] Rule normalization report.
* [ ] Risk assumption report.
* [ ] Cost/execution assumption report.
* [ ] Test plan artifact.
* [ ] Research evidence references.

### 13.3 Checklist

* [ ] Create `agents/strategy_development/strategy_reviewer_agent`.
* [ ] Review strategy spec completeness.
* [ ] Review strategy code structure.
* [ ] Review generated file manifest.
* [ ] Review `BaseStrategy` inheritance.
* [ ] Review `StatefulStrategyMixin` inheritance when required.
* [ ] Review `strategy_name`.
* [ ] Review `strategy_type`.
* [ ] Review schema versions.
* [ ] Review parameter loading.
* [ ] Review parameter casting.
* [ ] Review parameter validation.
* [ ] Review `on_init()`.
* [ ] Review `on_bar()`.
* [ ] Review `_calculate_indicators()`.
* [ ] Review `_shift_features()`.
* [ ] Review `_ensure_signal_columns()`.
* [ ] Review `_generate_simple_signals()`.
* [ ] Review `_generate_event_activators()`.
* [ ] Review `get_signal()`.
* [ ] Review `on_event()` when applicable.
* [ ] Review state initialization.
* [ ] Review side-specific state.
* [ ] Review state reset logic.
* [ ] Review `TradeAction` creation.
* [ ] Review `TradeAction` metadata.
* [ ] Review setup ID logic.
* [ ] Review group ID logic.
* [ ] Review parent/child metadata for decomposition.
* [ ] Review martingale step caps.
* [ ] Review pyramiding caps.
* [ ] Review grid/hedge caps.
* [ ] Review no-lookahead handling.
* [ ] Review multi-timeframe alignment.
* [ ] Review spread/slippage assumptions in README/config.
* [ ] Review cost assumptions in README/config.
* [ ] Review risk-control compatibility.
* [ ] Review forbidden broker/execution calls.
* [ ] Review forbidden risk approval logic.
* [ ] Review forbidden live portfolio mutation.
* [ ] Review tests.
* [ ] Review README.
* [ ] Output review report.
* [ ] Output required fixes.
* [ ] Output approval status for backtesting handoff.

### 13.4 Strategy Reviewer LLM Responsibilities

* [ ] Explain code issues.
* [ ] Summarize reviewer findings.
* [ ] Suggest fixes.
* [ ] Identify implementation inconsistencies.
* [ ] Identify strategy-template violations.
* [ ] Identify ambiguous code behavior.

### 13.5 Strategy Reviewer Deterministic Policy Rules

* [ ] Reject if standard strategy files are missing.
* [ ] Reject if required tests are missing.
* [ ] Reject if `on_bar()` does not guarantee standard signal columns.
* [ ] Reject if current-bar execution uses unshifted current-bar information.
* [ ] Reject if stateful strategy lacks `on_event()`.
* [ ] Reject if complex strategy fails to use `on_bar()` activators.
* [ ] Reject if `TradeAction` metadata is missing.
* [ ] Reject if group IDs are missing for multi-position logic.
* [ ] Reject if state reset is missing for basket/group strategies.
* [ ] Reject if broker APIs are called directly.
* [ ] Reject if strategy approves risk internally.
* [ ] Reject if code mutates portfolio state directly.
* [ ] Reject if parameter validation is missing.
* [ ] Reject if tests cannot serialize or run.
* [ ] Approve for backtesting only when structure, contracts, safety, and tests pass.

### 13.6 Output Artifacts

* [ ] Code review report.
* [ ] Strategy-template compliance report.
* [ ] Safety review report.
* [ ] No-lookahead review report.
* [ ] Test completeness report.
* [ ] Fix list.
* [ ] Backtesting handoff readiness status.

---

## 14. Strategy Spec Storage Agent

### 14.1 Purpose

Persist strategy specs, versions, lineage, and lifecycle state.

### 14.2 Checklist

* [ ] Create `agents/strategy_development/strategy_spec_storage_agent`.
* [ ] Save spec to database.
* [ ] Save spec to `memory/strategies/`.
* [ ] Save spec as JSON.
* [ ] Save spec as YAML where useful.
* [ ] Version each spec.
* [ ] Link spec to research evidence.
* [ ] Link spec to research report ID.
* [ ] Link spec to hypothesis ID.
* [ ] Link spec to user request ID.
* [ ] Link spec to generated code package.
* [ ] Link spec to review report.
* [ ] Assign lifecycle state `spec`.
* [ ] Assign lifecycle state `approved_for_codegen`.
* [ ] Assign lifecycle state `generated_pending_review`.
* [ ] Assign lifecycle state `review_failed`.
* [ ] Assign lifecycle state `approved_for_backtest`.
* [ ] Maintain version history.
* [ ] Maintain audit history.
* [ ] Output storage receipt.

### 14.3 Deterministic Policy Rules

* [ ] Do not overwrite prior spec versions without version increment.
* [ ] Do not store a spec without schema validation.
* [ ] Do not mark `approved_for_codegen` unless validation passed.
* [ ] Do not mark `approved_for_backtest` unless reviewer passed.
* [ ] Do not remove rejected or failed versions from memory.

---

## 15. Strategy Code Storage Agent

### 15.1 Purpose

Persist generated strategy code artifacts and link them to specs and review results.

### 15.2 Checklist

* [ ] Create `agents/strategy_development/strategy_code_storage_agent`.
* [ ] Save generated strategy package.
* [ ] Save generated file manifest.
* [ ] Save generated tests.
* [ ] Save generated README.
* [ ] Save codegen assumptions.
* [ ] Save codegen warnings.
* [ ] Link code package to spec ID.
* [ ] Link code package to strategy version.
* [ ] Link code package to review report.
* [ ] Track code lifecycle state.
* [ ] Track generated files checksum.
* [ ] Track generator prompt version.
* [ ] Track policy version.
* [ ] Output code storage receipt.

### 15.3 Deterministic Policy Rules

* [ ] Do not store code without a valid spec ID.
* [ ] Do not overwrite generated strategy code without a new version.
* [ ] Do not mark code approved unless reviewer passes.
* [ ] Do not persist generated code if it contains blocked imports or direct execution calls.

---

## 16. Strategy Handoff Agent

### 16.1 Purpose

Package approved strategy specs and reviewed code for Validation & Backtesting Department.

### 16.2 Checklist

* [ ] Create `agents/strategy_development/strategy_handoff_agent`.
* [ ] Create handoff payload for Backtest Agent.
* [ ] Include strategy spec ID.
* [ ] Include code package ID.
* [ ] Include strategy version.
* [ ] Include generated file manifest.
* [ ] Include target symbol.
* [ ] Include target timeframe.
* [ ] Include data requirements.
* [ ] Include cost assumptions.
* [ ] Include execution assumptions.
* [ ] Include risk assumptions.
* [ ] Include test plan.
* [ ] Include robustness requirements.
* [ ] Include research evidence references.
* [ ] Include reviewer status.
* [ ] Include known limitations.
* [ ] Include expected failure modes.
* [ ] Include lifecycle state.
* [ ] Output handoff package.

### 16.3 Deterministic Policy Rules

* [ ] Handoff only if spec status is `approved_for_backtest`.
* [ ] Handoff only if generated code package exists.
* [ ] Handoff only if Strategy Reviewer approved.
* [ ] Handoff only if required tests exist.
* [ ] Handoff only if cost and risk assumptions exist.
* [ ] Handoff only if evidence lineage exists.

---

## 17. Shared Contracts

### 17.1 StrategySpec

The Strategy Creation Department should standardize a `StrategySpec` contract.

Required fields:

* [ ] `spec_id`.
* [ ] `strategy_name`.
* [ ] `strategy_family`.
* [ ] `strategy_type`.
* [ ] `lifecycle_state`.
* [ ] `symbol`.
* [ ] `asset_class`.
* [ ] `timeframe`.
* [ ] `execution_timeframe`.
* [ ] `signal_timeframe`.
* [ ] `filter_timeframe`.
* [ ] `higher_timeframe`.
* [ ] `lower_timeframe`.
* [ ] `market_regime`.
* [ ] `research_question`.
* [ ] `hypothesis_id`.
* [ ] `research_report_ids`.
* [ ] `evidence_refs`.
* [ ] `entry_rules`.
* [ ] `exit_rules`.
* [ ] `pending_order_rules`.
* [ ] `cancel_order_rules`.
* [ ] `position_sizing_rules`.
* [ ] `position_management_rules`.
* [ ] `risk_controls`.
* [ ] `cost_assumptions`.
* [ ] `execution_assumptions`.
* [ ] `data_requirements`.
* [ ] `indicator_requirements`.
* [ ] `state_requirements`.
* [ ] `signal_columns`.
* [ ] `activator_columns`.
* [ ] `trade_action_types`.
* [ ] `parameter_schema`.
* [ ] `parameter_defaults`.
* [ ] `parameter_validation_rules`.
* [ ] `lookahead_handling`.
* [ ] `invalidation_rules`.
* [ ] `test_plan`.
* [ ] `robustness_plan`.
* [ ] `expected_failure_modes`.
* [ ] `generated_files_expected`.
* [ ] `created_at`.
* [ ] `created_by_agent`.
* [ ] `version`.

### 17.2 StrategyImplementationBrief

Required fields:

* [ ] `brief_id`.
* [ ] `spec_id`.
* [ ] `template_type`.
* [ ] `base_classes`.
* [ ] `required_imports`.
* [ ] `strategy_file_path`.
* [ ] `config_file_path`.
* [ ] `readme_file_path`.
* [ ] `test_file_paths`.
* [ ] `methods_to_implement`.
* [ ] `signal_columns_to_generate`.
* [ ] `activator_columns_to_generate`.
* [ ] `state_fields`.
* [ ] `trade_action_metadata_fields`.
* [ ] `risk_control_fields`.
* [ ] `lookahead_rules`.

### 17.3 StrategyCodePackage

Required fields:

* [ ] `code_package_id`.
* [ ] `spec_id`.
* [ ] `strategy_version`.
* [ ] `files`.
* [ ] `file_manifest`.
* [ ] `generated_tests`.
* [ ] `readme`.
* [ ] `codegen_warnings`.
* [ ] `blocked_imports_detected`.
* [ ] `direct_execution_calls_detected`.
* [ ] `risk_approval_calls_detected`.
* [ ] `status`.

### 17.4 StrategyReviewReport

Required fields:

* [ ] `review_id`.
* [ ] `spec_id`.
* [ ] `code_package_id`.
* [ ] `review_status`.
* [ ] `blocking_issues`.
* [ ] `non_blocking_issues`.
* [ ] `template_compliance_score`.
* [ ] `contract_compliance_score`.
* [ ] `lookahead_safety_score`.
* [ ] `risk_compatibility_score`.
* [ ] `test_completeness_score`.
* [ ] `readiness_for_backtest`.
* [ ] `required_fixes`.
* [ ] `audit_refs`.

---

## 18. Department Permissions

### 18.1 Allowed Actions

* [ ] Read research reports.
* [ ] Read approved hypotheses.
* [ ] Read strategy memory.
* [ ] Read rejected strategy memory.
* [ ] Read current strategy template standards.
* [ ] Generate strategy specs.
* [ ] Generate strategy code artifacts.
* [ ] Generate tests.
* [ ] Generate README files.
* [ ] Save specs to strategy memory.
* [ ] Save generated code artifacts.
* [ ] Review generated strategy code.
* [ ] Create validation/backtesting handoff packages.

### 18.2 Forbidden Actions

* [ ] Execute trades.
* [ ] Send orders to MT5/cTrader.
* [ ] Approve risk.
* [ ] Override Risk Governor.
* [ ] Modify live portfolio.
* [ ] Modify broker configuration.
* [ ] Deploy strategy to production.
* [ ] Mark strategy as live-approved.
* [ ] Bypass Validation & Backtesting Department.
* [ ] Bypass Risk & Portfolio Department.

### 18.3 Permission Profiles

* [ ] `strategy_creation_read_only_v1`.
* [ ] `strategy_spec_write_v1`.
* [ ] `strategy_codegen_write_v1`.
* [ ] `strategy_review_read_only_v1`.
* [ ] `strategy_handoff_write_v1`.

---

## 19. Department Audit Requirements

Every agent response must include:

* [ ] `request_id`.
* [ ] `agent_name`.
* [ ] `department`.
* [ ] `prompt_version`.
* [ ] `policy_version`.
* [ ] `llm_used`.
* [ ] `tools_called`.
* [ ] `permission_profile`.
* [ ] `context_revision`.
* [ ] `evidence_refs`.
* [ ] `research_report_ids`.
* [ ] `spec_id` where applicable.
* [ ] `code_package_id` where applicable.
* [ ] `review_id` where applicable.
* [ ] `model_provider`.
* [ ] `model_name`.
* [ ] `fallback_used`.
* [ ] `lifecycle_state_before`.
* [ ] `lifecycle_state_after`.
* [ ] `decision`.
* [ ] `risk_level`.
* [ ] `allowed_actions`.
* [ ] `blocked_actions`.
* [ ] `reasons`.

---

## 20. Department Evaluation Requirements

### 20.1 Agent-Level Tests

Every department agent must include:

* [ ] `test_contracts.py`.
* [ ] `test_deterministic_policy.py`.
* [ ] `test_service.py`.
* [ ] `test_agent_smoke.py`.

### 20.2 Strategy Creator Tests

* [ ] Valid prompt becomes valid `StrategySpec`.
* [ ] Approved research hypothesis becomes valid `StrategySpec`.
* [ ] Missing symbol returns `NEEDS_MORE_CONTEXT`.
* [ ] Missing timeframe returns `NEEDS_MORE_CONTEXT`.
* [ ] Untestable strategy is rejected.
* [ ] Future-looking strategy is rejected.
* [ ] Complex strategy includes `on_event()` requirement.
* [ ] Simple strategy includes `get_signal()` path.

### 20.3 Strategy Codegen Tests

* [ ] Codegen rejects unapproved spec.
* [ ] Codegen generates required files.
* [ ] Codegen generates required tests.
* [ ] Codegen generates standard signal columns.
* [ ] Codegen shifts indicators to avoid lookahead.
* [ ] Codegen does not generate broker calls.
* [ ] Codegen does not generate risk approval calls.
* [ ] Codegen marks output `generated_pending_review`.

### 20.4 Strategy Reviewer Tests

* [ ] Reviewer rejects missing files.
* [ ] Reviewer rejects missing tests.
* [ ] Reviewer rejects missing signal columns.
* [ ] Reviewer rejects lookahead-prone code.
* [ ] Reviewer rejects direct broker calls.
* [ ] Reviewer rejects internal risk approval.
* [ ] Reviewer rejects missing action metadata.
* [ ] Reviewer approves compliant strategy package for backtesting.

---

## 21. Department Workflow

```mermaid
flowchart TD
    A[User Prompt or Research Hypothesis] --> B[Strategy Creation Orchestrator]
    B --> C[Strategy Creator Agent]
    C --> D[Strategy Rule Normalizer Agent]
    D --> E[Strategy Template Selector Agent]
    E --> F[Strategy Risk Assumption Agent]
    F --> G[Strategy Cost & Execution Assumption Agent]
    G --> H[Strategy Test Plan Agent]
    H --> I[Strategy Spec Validator Agent]
    I --> J{Spec Approved for Codegen?}
    J -->|No| K[Revision Required]
    J -->|Yes| L[Strategy Codegen Agent]
    L --> M[Strategy Reviewer Agent]
    M --> N{Approved for Backtest?}
    N -->|No| O[Fix Required]
    N -->|Yes| P[Strategy Spec Storage Agent]
    P --> Q[Strategy Code Storage Agent]
    Q --> R[Strategy Handoff Agent]
    R --> S[Validation & Backtesting Department]
```

---

## 22. Recommended Build Order

* [ ] Create shared contracts for Strategy Creation Department.
* [ ] Create `StrategySpec` schema.
* [ ] Create `StrategyImplementationBrief` schema.
* [ ] Create `StrategyCodePackage` schema.
* [ ] Create `StrategyReviewReport` schema.
* [ ] Create Strategy Creator Agent.
* [ ] Create Strategy Spec Validator Agent.
* [ ] Create Strategy Rule Normalizer Agent.
* [ ] Create Strategy Template Selector Agent.
* [ ] Create Strategy Risk Assumption Agent.
* [ ] Create Strategy Cost & Execution Assumption Agent.
* [ ] Create Strategy Test Plan Agent.
* [ ] Create Strategy Codegen Agent.
* [ ] Create Strategy Reviewer Agent.
* [ ] Create Strategy Spec Storage Agent.
* [ ] Create Strategy Code Storage Agent.
* [ ] Create Strategy Handoff Agent.
* [ ] Create Strategy Creation Orchestrator Agent.
* [ ] Register Strategy Creation Orchestrator with Planner.
* [ ] Surface final summaries only through CEO Agent and CEOChatGateway.

---

## 23. Department Definition of Done

The Strategy Creation Department is complete when:

* [ ] A request like `create a EURUSD H1 mean-reversion strategy` becomes a structured strategy spec.
* [ ] The strategy spec passes deterministic validation.
* [ ] The strategy spec uses HaruQuant strategy-template conventions.
* [ ] The strategy spec defines `on_bar()` responsibilities.
* [ ] The strategy spec defines `get_signal()` responsibilities where applicable.
* [ ] The strategy spec defines `on_event()` responsibilities where applicable.
* [ ] The strategy spec defines standard signal columns.
* [ ] The strategy spec defines activator columns for complex strategies.
* [ ] The strategy spec defines parameters and validation rules.
* [ ] The strategy spec defines cost assumptions.
* [ ] The strategy spec defines execution assumptions.
* [ ] The strategy spec defines risk assumptions.
* [ ] The strategy spec defines test plan and robustness plan.
* [ ] The Strategy Codegen Agent can generate a compliant strategy package.
* [ ] The generated strategy package includes strategy code, config, README, and tests.
* [ ] The Strategy Reviewer Agent can approve or reject the generated package deterministically.
* [ ] The department can save specs and generated code with version history.
* [ ] The department can create a handoff package for Validation & Backtesting Department.
* [ ] Every agent returns the standard `AgentResponse` envelope.
* [ ] Every agent has deterministic policy rules.
* [ ] Every agent has audit metadata.
* [ ] Every agent has evaluator checks.
* [ ] Every agent has required tests.
* [ ] No department agent can execute trades.
* [ ] No department agent can approve risk.
* [ ] No department agent can bypass CEO/Planner orchestration.

---

## 24. Final Rule

The Strategy Creation Department must make strategy creation deterministic, testable, reviewable, and safe:

```text
Research creates hypotheses.
Strategy Creator creates the spec.
Strategy Codegen creates implementation artifacts.
Strategy Reviewer blocks unsafe or non-compliant code.
Backtesting proves or rejects the strategy historically.
Risk Governor approves or rejects risk later.
Execution Bridge executes only approved actions later.
```

The department succeeds when strategy ideas stop being vague prompts and become auditable, versioned, code-ready trading systems that follow HaruQuant's strategy lifecycle.

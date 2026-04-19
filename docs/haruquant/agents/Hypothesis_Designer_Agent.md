# Hypothesis Designer Agent

This document is the full implementation and operating specification for the
HaruQuant `hypothesis_designer_agent`.

It covers the purpose of the agent, the contract it emits, the deterministic
defaulting rules behind it, the materialization path into the strategy catalog
and governance registry, and the current script-based end-to-end usage flow.

## Purpose

The Hypothesis Designer Agent closes the gap between:

- a rough human trading idea
- a complete, testable strategy definition

Its job is to convert ambiguous research intent into a machine-readable
`StrategyBlueprint` that HaruQuant can validate, render into a strategy code
scaffold, and register in the strategy catalog and governance registry.

This agent operates before backtesting and before any live execution path.

It does not:

- place orders
- run backtests
- approve promotion
- mutate broker state

It does:

- classify the strategy type
- fill logical gaps with deterministic defaults
- force entry, exit, risk, and sizing rules into explicit form
- produce a governed contract that downstream systems can trust

## Role In The HaruQuant Flow

Current implemented flow:

1. User submits rough idea
2. `hypothesis_designer_agent` produces `StrategyBlueprint`
3. `StrategyBlueprintValidator` normalizes and validates the contract
4. `StrategyBlueprintRenderer` renders a Python strategy scaffold
5. `StrategyBlueprintMaterializationService` registers the strategy through the
   existing catalog flow
6. Strategy is persisted in the governance registry with lifecycle state
   `RESEARCH`
7. Strategy version folder stores:
   - `strategy.py`
   - `metadata.json`
   - `strategy_blueprint.json`

## Source Files

### Agent wrapper

- [backend/agents/hypothesis_designer_agent.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\hypothesis_designer_agent.py)

### Prompt / rulebook

- [backend/agents/prompts/hypothesis_designer_template.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\prompts\hypothesis_designer_template.py)

### Contract

- [backend/contracts/strategy_blueprint/model.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\contracts\strategy_blueprint\model.py)
- [backend/contracts/strategy_blueprint/README.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\contracts\strategy_blueprint\README.md)
- [backend/contracts/strategy_blueprint/schema.json](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\contracts\strategy_blueprint\schema.json)

### Design services

- [backend/services/strategy/design/blueprint_defaults.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy\design\blueprint_defaults.py)
- [backend/services/strategy/design/blueprint_validator.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy\design\blueprint_validator.py)
- [backend/services/strategy/design/blueprint_renderer.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy\design\blueprint_renderer.py)
- [backend/services/strategy/design/blueprint_materializer.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy\design\blueprint_materializer.py)

### Workflow

- [backend/orchestration/workflow/definitions/hypothesis_design.yaml](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\orchestration\workflow\definitions\hypothesis_design.yaml)

### Usage example

- [backend/scripts/examples/agentic_ai/05_agents_systems.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\05_agents_systems.py)

## Agent Identity

- Agent name: `hypothesis_designer_agent`
- Public wrapper: `HypothesisDesignerAgentWrapper`
- Instruction symbol: `HYPOTHESIS_DESIGNER_AGENT_INSTRUCTION`
- Output contract: `StrategyBlueprint`

## Input Surface

The agent wrapper accepts an `ADKRunRequest`.

Current expected input payload:

```python
{
    "idea": "Buy when RSI is low and exit when it recovers."
}
```

In the current example script, this idea is collected from CLI input and passed
into the wrapper through the example runtime.

## Output Contract

The agent emits a canonical `StrategyBlueprint` envelope with a payload that
captures:

- `strategy_id`
- `strategy_name`
- `source_idea`
- `strategy_type`
- `asset_scope`
- `entry_logic`
- `exit_logic`
- `risk_management`
- `position_sizing`
- `model_spec` when needed
- `portfolio_construction` when needed
- `assumptions_applied`
- `assumption_defaults_used`
- `backtest_readiness`
- `render_target`

This contract is the handoff point between rough idea intake and executable
strategy system assembly.

## Supported Strategy Types

The contract currently supports these `strategy_type` values:

- `technical`
- `portfolio`
- `ml`
- `factor`
- `stat_arb`
- `allocation`
- `rotation`

The most complete deterministic support today is for:

- technical
- portfolio
- ml

## Rulebook And Deterministic Defaults

The prompt defines the agent’s behavior contractually, but the actual safety net
is enforced in deterministic code by `StrategyBlueprintValidator`.

### Asset defaults

- Single-asset ideas default to `SPY`
- Portfolio-like ideas default to the HaruQuant large-cap universe
- Default timeframe is `1D`

### Indicator defaults

- If RSI is referenced without parameters, it defaults to `14`

### Risk defaults

Unless explicitly disabled:

- single-asset strategies default to:
  - `7% below entry price` stop-loss
  - `10% above entry price` take-profit
- portfolio-style strategies default to:
  - `7% portfolio-level drawdown stop or per-asset 7% stop-loss`
  - `10% per-asset take-profit or rebalance-driven profit capture`

### Position sizing defaults

- Single-asset strategies default to full capital
- Portfolio / allocation / rotation strategies default to equal weight
- Leverage defaults to `1.0`

### ML defaults

If the idea is ML-based and under-specified, the validator defaults to:

- `DecisionTreeClassifier`
- target: predict whether next-day return is positive or negative
- features:
  - `return_1d`
  - `volume`
  - `rsi_14`
  - `sma_20_gap`
- horizon: `1D ahead`

### Portfolio defaults

Portfolio-like strategies get default portfolio construction when missing:

- method: `HRP` if the idea references HRP, otherwise `EqualWeight`
- rebalance frequency: `Weekly`
- objective: `Risk-balanced diversified allocation`

## Readiness Semantics

`backtest_readiness` can currently be:

- `ready`
- `needs_review`

The validator marks blueprints as `needs_review` if required structure still
cannot be made complete enough for reliable downstream use.

## Materialization Into Strategy Catalog

The Hypothesis Designer does not stop at contract generation anymore.

`StrategyBlueprintMaterializationService`:

1. validates the blueprint again
2. renders Python strategy code
3. creates a real strategy via `StrategyCatalogService`
4. lets the catalog path upsert governance state
5. writes `strategy_blueprint.json` into the active version directory
6. enriches `metadata.json` with blueprint summary and readiness metadata

This is intentionally aligned with HaruQuant’s existing strategy persistence
path rather than inventing a separate research-only store.

## Governance Integration

Registration occurs through the existing catalog path:

- catalog strategy row is created
- initial strategy version is stored
- governance strategy ID is derived as `strategy:{user_id}:{strategy_id}`
- governance registry lifecycle starts at `RESEARCH`

This means blueprint-originated strategies are immediately visible to existing
catalog and operator governance surfaces.

## Workflow Definition

The YAML workflow for this agent is:

1. `define_strategy_blueprint`
2. `validate_strategy_blueprint`
3. `render_strategy_scaffold`
4. `register_strategy_catalog_entry`
5. `register_governance_strategy`
6. `review_backtest_readiness`

Current file:

- [backend/orchestration/workflow/definitions/hypothesis_design.yaml](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\orchestration\workflow\definitions\hypothesis_design.yaml)

This is the declarative Phase 2 flow for rough strategy intake.

## Example End-To-End Usage

The current runnable script is:

- [backend/scripts/examples/agentic_ai/05_agents_systems.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\05_agents_systems.py)

It now supports:

- CLI prompt for rough user idea
- default fallback idea when no input is provided
- blueprint generation
- render preview
- real catalog registration
- real governance registration

## Current Limitations

- No API endpoint yet for idea submission
- No UI yet for hypothesis design intake
- No backtest execution agent chained after materialization
- No promotion/evidence automation from this workflow yet
- `factor` and `stat_arb` types are represented in the contract but not yet as
  deeply enriched as technical, portfolio, and ML blueprints

## Next Recommended Agent

The natural follow-up agent is a Backtest Designer / Backtest Runner agent that:

- consumes `StrategyBlueprint`
- builds an executable backtest specification
- runs the backtest through HaruQuant services
- persists evidence for lifecycle progression from `RESEARCH` to
  `BACKTEST_QUALIFIED`

## Documentation Rule For Future Agents

Every new agent added to HaruQuant should ship with:

1. agent wrapper implementation
2. prompt/rulebook source
3. output contract documentation
4. workflow definition documentation
5. runnable example
6. dedicated agent spec document under `docs/haruquant/agents/`


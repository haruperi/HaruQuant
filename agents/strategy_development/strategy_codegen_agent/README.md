# Strategy Codegen Agent

## Purpose

Generates HaruQuant-compatible strategy code artifacts from approved StrategySpec objects.

## Department

Strategy Creation Department

## Allowed Actions

- `generate_strategy_code_package`
- `generate_strategy_tests`
- `generate_strategy_readme`
- `mark_generated_pending_review`

## Forbidden Actions

- `execute_trade`
- `send_order`
- `approve_risk`
- `override_risk_governor`
- `deploy_strategy_to_production`

## Tools

- `read_approved_strategy_spec`
- `write_generated_code_artifacts`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

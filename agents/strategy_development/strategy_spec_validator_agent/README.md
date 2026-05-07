# Strategy Spec Validator Agent

## Purpose

Validates that a StrategySpec is complete, testable, non-vague, and compatible with HaruQuant templates.

## Department

Strategy Creation Department

## Allowed Actions

- `validate_strategy_spec`
- `reject_incomplete_spec`
- `approve_spec_for_codegen`

## Forbidden Actions

- `execute_trade`
- `send_order`
- `approve_risk`
- `override_risk_governor`
- `deploy_strategy_to_production`

## Tools

- `read_strategy_spec`
- `validate_strategy_template_rules`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

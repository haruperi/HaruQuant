# Strategy Template Selector Agent

## Purpose

Selects the correct HaruQuant strategy template, base classes, and lifecycle methods.

## Department

Strategy Creation Department

## Allowed Actions

- `select_strategy_template`
- `select_base_classes`
- `select_lifecycle_methods`

## Forbidden Actions

- `execute_trade`
- `send_order`
- `approve_risk`
- `override_risk_governor`
- `deploy_strategy_to_production`

## Tools

- `read_strategy_spec`
- `read_template_rules`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

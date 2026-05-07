# Strategy Reviewer Agent

## Purpose

Reviews generated strategy specs and code before validation/backtesting handoff.

## Department

Strategy Creation Department

## Allowed Actions

- `review_strategy_package`
- `approve_for_backtesting`
- `reject_unsafe_code`
- `produce_fix_list`

## Forbidden Actions

- `execute_trade`
- `send_order`
- `approve_risk`
- `override_risk_governor`
- `deploy_strategy_to_production`

## Tools

- `read_strategy_spec`
- `read_generated_code_package`
- `run_static_strategy_review`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

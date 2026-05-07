# Strategy Spec Storage Agent

## Purpose

Persists strategy specs, versions, lineage, and lifecycle state.

## Department

Strategy Creation Department

## Allowed Actions

- `save_strategy_spec`
- `version_strategy_spec`
- `link_spec_lineage`

## Forbidden Actions

- `execute_trade`
- `send_order`
- `approve_risk`
- `override_risk_governor`
- `deploy_strategy_to_production`

## Tools

- `read_strategy_spec`
- `write_strategy_memory`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.
